# IntentLock Combined Phase 5–7 — Core Release

This build combines the transaction kernel, agent identity, payment gating, replay/idempotency, recovery, audit, Transaction Passport, Attack Lab, and real Dashboard work into one version on top of Phase 4.

## What is real in this build

### Merchant / agent commerce
- Existing Phase 4 auth, merchant onboarding, CSV/JSON catalog upload, merchant policy, Ed25519 merchant identity, and agent discovery remain intact.
- Discovery now advertises real REST catalog, checkout, and transaction endpoints.
- Public checkout creation persists a merchant-authoritative `CheckoutSnapshot` and returns its `checkout_id` + SHA-256 `checkout_hash`.
- External agents can be registered with an Ed25519 public key.
- A registered external agent can sign and submit a public transaction request against the merchant's real checkout snapshot.
- REST is implemented. ACP/UCP/MCP/x402 are explicitly `PLANNED`; this build does not claim protocol conformance that it does not implement.

### Human authority + deterministic IntentLock
- Natural-language intent is compiled into bounded product/category/brand/amount/quantity constraints.
- Human authorization creates a cryptographically signed mandate.
- Reference Buyer requests are Ed25519 signed.
- The signed agent envelope binds `agent_id`, `mandate_id`, SKU, quantity, `checkout_id`, `checkout_hash`, nonce, and timestamp.
- Merchant catalog is authoritative for price; the agent proposes SKU + quantity, not the payable price.
- The deterministic kernel evaluates all controls rather than stopping at the first failure.
- Decisions are `ALLOW`, `BLOCKED`, or `STEP-UP`.
- Only `ALLOW` can create a payment order.

## Kernel controls

The evaluator currently records these controls:

1. Agent Identity / Ed25519 request signature
2. Request Freshness
3. Replay nonce
4. Human Mandate signature
5. Mandate Binding (intent + merchant + agent)
6. Mandate Expiry
7. Mandate State / consumption
8. Merchant / payee
9. Checkout Request Binding (signed SKU/quantity ↔ checkout snapshot)
10. Brand
11. Category
12. Quantity
13. Inventory
14. Amount
15. Price Authority
16. Checkout Integrity
17. Merchant Transaction Limit
18. Step-Up Threshold
19. Daily Spend
20. Recovery Lineage (when recovery is attempted)

Blocked or step-up actions never create a payment order. A blocked valid-agent request still consumes its transport nonce, so it cannot simply be replayed.

## Idempotency and replay

- Stable merchant-scoped idempotency keys are checked before replay handling.
- Three deliveries of the same economic action return one transaction/order and increment the duplicate count instead of charging three times.
- Reusing a nonce with a different idempotency key is recorded as a replay and blocked.
- A consumed mandate cannot be reused for a new root economic action.

## Payment modes

### `LOCAL_TEST` — default
No external account or paid API key is required. IntentLock creates local test order IDs and the frontend can simulate captured/failed outcomes. Local simulation is explicitly recorded as local evidence and reports **Razorpay API calls = 0**.

### `RAZORPAY_TEST`
Add free Razorpay Test Mode credentials to `backend/.env`:

```env
RAZORPAY_KEY_ID=rzp_test_...
RAZORPAY_KEY_SECRET=...
RAZORPAY_WEBHOOK_SECRET=...
```

With credentials configured:
- `ALLOW` creates a real Razorpay Test Mode order.
- Buyer Demo loads Razorpay Checkout.
- Backend verifies the Razorpay Checkout HMAC signature.
- Webhook endpoint requires a configured webhook secret and verifies its HMAC before applying state.
- Webhook amount/currency must match the authorized order.
- Payment state transitions are guarded so a captured transaction cannot regress to failed/authorized.
- Duplicate webhook delivery of the same state is idempotent.

The actual network Razorpay path requires your own free Test Mode credentials and internet; the included automated suite validates local-mode gating and the backend logic without pretending to have contacted Razorpay.

## Recovery

- A failed payment creates a recovery case.
- Recovery first requires authoritative state `FAILED`.
- It uses the original intent + signed mandate.
- The recovery candidate gets a new merchant-authoritative checkout and a fresh signed agent request.
- It re-enters the same IntentLock kernel.
- Recovery lineage is checked.
- An out-of-authority recovery remains blocked.

## Tamper-evident audit + Passport

- Intent, mandate, kernel, payment, replay/idempotency, recovery and attack events append to a SHA-256 hash-linked ledger.
- `POST /api/v1/audit/verify` recomputes the chain and detects tampering.
- Transaction Passport reads actual intent, mandate, checkout hash, authoritative price, policy checks, payment evidence and audit events from the database.

## Real Attack Lab

The frontend now executes the same backend kernel for:
- Prompt Injection (compromised output / quantity escalation)
- Quantity Escalation
- Wrong Product
- Checkout Mutation
- Forged Agent Signature
- Wrong Merchant
- Replay Mandate
- Duplicate Invocation
- Expired Authorization
- Unauthorized Recovery

The checkout-mutation scenario is deliberately signed by a valid agent with a bad checkout hash, proving the failure is **Checkout Integrity**, not merely an invalid signature.

## Dashboard

Transaction/enforcement/payment/recovery/audit telemetry is database-derived:
- economic actions
- captured/recovered GMV
- ALLOW / BLOCKED / STEP-UP / RECOVERED
- unsafe attempted GMV
- actions blocked before Razorpay
- duplicates prevented
- replay attempts rejected
- registered agents
- real recent transactions
- real audit/live events
- recovery cases
- payment execution mode
- webhook readiness
- audit-chain integrity
- critical control failures (for example, payment order behind a non-ALLOW action or audit tampering)

The public landing page still contains illustrative marketing/demo examples by design. Merchant Console operational telemetry is API-backed.

## Reference Buyer

The Buyer Demo uses the merchant's real uploaded catalog and a deterministic tool-oriented planner. It emits a tool trace such as:

```text
discover_merchant()
search_catalog()
check_inventory()
get_product()
create_checkout_proposal()
```

No paid LLM is required for this build. The planner is intentionally deterministic for a reproducible hackathon demo; an optional LLM planner can be added later without giving the LLM payment authority.

## Run

Frontend:

```powershell
npm install
npm run dev
```

Backend:

```powershell
cd backend
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Open:
- Frontend: `http://localhost:3000`
- API docs: `http://localhost:8000/docs`

For a fresh combined build, starting with a fresh local SQLite database is recommended. The app creates it automatically.

## Suggested end-to-end walkthrough

1. Register a new merchant.
2. Complete all six onboarding steps and upload a real CSV catalog.
3. Open Buyer Demo and enter a shopping request against that catalog.
4. Reference Buyer selects a real in-stock SKU and shows its tool trace.
5. Authorize the exact purchase.
6. IntentLock creates intent + signed mandate + authoritative checkout + signed agent request and evaluates all rules.
7. In `LOCAL_TEST`, capture the payment or deliberately simulate failure.
8. Open Transaction Passport and inspect real evidence.
9. Run `Quantity Escalation` in Attack Lab and verify `BLOCKED` + `Razorpay API calls: 0`.
10. Run `Checkout Mutation`: Agent Identity should PASS while Checkout Integrity FAILS.
11. Run `Forged Agent Signature`: Agent Identity should FAIL.
12. Run `Duplicate Invocation`: 3 requests → 1 economic action/payment order.
13. Run `Replay Mandate`: replay/consumption controls should fail.
14. From a failed payment, open Recovery Center and re-evaluate a candidate within original authority.
15. Open Audit Log and click Verify Chain.
16. Return to Dashboard; the operational metrics should reflect the actions actually performed.

## Automated verification

Current backend suite: **34 tests passing**.

Coverage includes Phase 4 functionality plus valid transactions, quantity/amount attacks, checkout mutation with valid agent signature, forged signatures, external signed-agent public transactions, idempotency, replay, step-up gating/approval, local payment state, recovery, Buyer planning, Dashboard metrics, audit verification and tamper detection.
