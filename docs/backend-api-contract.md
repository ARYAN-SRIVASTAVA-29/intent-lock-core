# IntentLock frontend → backend API contract

This contract is based on the current exported v0 frontend. The frontend currently has no real network calls; almost all operational data comes from `lib/intentlock-data.ts`, while the dashboard also owns local mock data in `components/dashboard/platform-dashboard.tsx`.

## Conventions

- Base URL: `/api/v1`
- Money is transported in **minor units** (`amount_minor`) rather than formatted strings.
- Currency: ISO code, initially `INR`.
- Backend returns machine states such as `ALLOW`, `BLOCKED`, `STEP_UP`, `CAPTURED` and the frontend formats labels.
- The AI may propose SKU and quantity. Merchant/backend data is authoritative for price, inventory, tax, shipping, discount and final total.
- Money-moving endpoints are never called directly by the buyer agent; all economic actions pass through IntentLock first.

## Screen mapping

| Frontend surface | Current source | Backend endpoint(s) |
|---|---|---|
| Dashboard | `platform-dashboard.tsx` local mocks + shared mocks | `GET /dashboard` |
| Catalog | `lib/intentlock-data.ts` | `GET /catalog/products`, `POST /catalog/import`, `POST /catalog/validate` |
| Transactions | `lib/intentlock-data.ts` | `GET /transactions` |
| Transaction Passport | shared transaction/audit mocks | `GET /transactions/{transaction_id}/passport` |
| Policies | hardcoded inputs | `GET /policies/current`, `PUT /policies/current`, `POST /policies/current/publish` |
| Agent Registry | `lib/intentlock-data.ts` | `GET /agents`, `GET /agents/{agent_id}` |
| Attack Lab | local component state | `POST /attack-lab/run` |
| Recovery | local utility mock | `GET /recovery/cases`, `POST /recovery/{case_id}/evaluate`, `POST /recovery/{case_id}/execute` |
| Audit Log | fake short hashes | `GET /audit/events`, `POST /audit/verify` |
| Buyer Demo | local authorization state | buyer-agent + intent + mandate + checkout APIs below |
| Onboarding Payment | local state only | `POST /onboarding/payment/test` |
| Onboarding Catalog | local state only | catalog endpoints |
| Onboarding Policy | local state only | policy endpoints |
| Onboarding Identity | local state only | `POST /merchant/identity/provision` |
| Onboarding Discovery | local state only | `GET /agent-commerce/discovery`, `POST /agent-commerce/discovery/test` |
| Onboarding Readiness | hardcoded PASS states | `GET /onboarding/readiness` |

## Core commerce endpoints

### Health

`GET /health`

Implemented in Phase 1.

### Agent discovery

`GET /agent-commerce/discovery`

Returns the merchant's machine-readable commerce capabilities, e.g. merchant identity, catalog endpoint, policy endpoint, checkout endpoint, supported protocol adapters and readiness.

### Agent-readable catalog

`GET /agent-commerce/catalog`

Read-only authoritative product view for compatible agents.

### Compile buyer intent

`POST /intents/compile`

Natural language → candidate structured intent. The LLM output is **not authority**.

### Create signed human mandate

`POST /mandates`

Creates a bounded authorization containing merchant, product/category/brand constraints, quantity, maximum amount, currency, expiry and nonce, then canonicalizes and signs it.

### Create authoritative checkout snapshot

`POST /checkouts`

Input from agent should be minimal, primarily SKU + quantity. Backend resolves authoritative commercial values and creates `checkout_hash`.

### Evaluate economic action

`POST /economic-actions/evaluate`

Input combines agent-signed request, mandate reference and checkout reference. Deterministic IntentLock rules return `ALLOW`, `BLOCKED` or `STEP_UP` with all rule results and reason codes. Evaluation does not short-circuit; every relevant rule is reported.

### Execute allowed economic action

`POST /economic-actions/{economic_action_id}/execute`

Only valid after `ALLOW`. Creates or reuses one Razorpay Test Mode order using stable economic-action idempotency.

## Razorpay endpoints

- `POST /payments/razorpay/verify`
- `POST /webhooks/razorpay`
- Internal order creation is reachable only from an allowed IntentLock economic action.

## Security primitives to implement

1. Ed25519 merchant and reference-agent identities.
2. Canonical JSON + SHA-256 hashing.
3. Signed bounded human mandates.
4. Agent request signature, timestamp and nonce verification.
5. Authoritative checkout snapshots.
6. Human Authority ∩ Merchant Policy.
7. Stable economic action ID that excludes volatile timestamps.
8. Replay protection and mandate state (`ACTIVE`, `CONSUMED`, `EXPIRED`, `REVOKED`).
9. Append-only hash-linked audit events.
10. Intent-preserving payment recovery that always re-enters IntentLock.

## Important current-frontend gaps found in the export

The current ZIP does **not** yet contain separate `/authorize/{intentId}` or `/execution/{transactionId}` routes. The buyer demo currently combines product review + a local "Authorize exact purchase" button. We should decide later whether to add those routes or keep the demo flow embedded in Buyer Demo.

The current Attack Lab lists multiple attack names, but only one shared local simulation is actually executed. Backend integration will make each attack call the real deterministic kernel.

The current Transaction Passport renders all six verification checks as PASS even when a blocked transaction is opened. This will disappear once the page consumes real per-rule backend evidence.

## Phase 4 additions

- `GET /api/v1/merchant` now returns authenticated merchant control-plane state, including real catalog summary, payment-test state, policy status, and Ed25519 identity metadata.
- `PUT /api/v1/policies/current` persists merchant policy changes.
- `POST /api/v1/agent-commerce/merchants/{merchant_id}/checkouts` creates a merchant-authoritative checkout proposal from `sku + quantity`; price is derived from merchant catalog data.
- Public agent catalog and policy endpoints remain closed until the merchant enables discovery.
- Dashboard catalog/discovery/payment/identity/policy status modules consume real backend state. Transaction/enforcement telemetry remains demo data until the transaction-kernel phases.
