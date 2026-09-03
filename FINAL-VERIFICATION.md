# IntentLock Combined Core Release — Final Verification

This archive is the consolidated build on top of Phase 4. It contains the previously planned Phase 5–7 functionality in one version.

## Verified in this workspace

- Backend automated suite: **34 / 34 tests passing**.
- FastAPI imports and route registration verified: **50 HTTP routes** including docs/system routes.
- Python source compilation verified.
- Frontend TypeScript/TSX syntax parse verified across all source files: **0 syntax diagnostics**.
- Scan of Merchant Console source found no legacy hard-coded operational telemetry values such as the old GMV / 24-products / 31-SKUs dashboard figures. Public landing-page examples remain illustrative by design.
- No real secrets are included in the archive.

## Backend capabilities in this release

- Merchant registration/login and protected Merchant Console
- Real merchant onboarding/catalog/policy/identity/discovery from Phase 4
- Agent-readable REST catalog and merchant discovery
- Merchant-authoritative checkout snapshots
- Natural-language intent compilation
- Signed bounded human mandates
- Ed25519 reference/external agent identity
- Signed agent request envelope binding checkout id/hash, SKU, quantity, mandate, nonce and timestamp
- Deterministic IntentLock rule engine with ALLOW / BLOCKED / STEP-UP
- Payment gating: only ALLOW can create a payment order
- Stable economic-action idempotency and duplicate containment
- Replay and consumed-mandate protection
- LOCAL_TEST payment mode with no API keys required
- Razorpay Test Mode order path when test credentials are supplied
- Razorpay checkout signature verification and webhook verification/state guards
- Failed-payment recovery that re-enters the same IntentLock authority checks
- SHA-256 hash-linked audit ledger and chain verification
- Transaction Passport backed by stored evidence
- Attack Lab backed by the real kernel
- Dashboard transaction/enforcement/payment/recovery/audit metrics backed by the database
- Reference Buyer against the merchant's uploaded catalog

## Important protocol truthfulness

- REST: implemented
- ACP: planned, not claimed as implemented
- UCP: planned
- MCP: planned
- x402: planned

## Frontend build note

A full `next build` could not be executed in the packaging container because dependency installation exceeded the available network execution window. The source itself was syntax-checked successfully. Run `npm install` and `npm run dev` (or `npm run build`) locally as the final browser/build verification. Earlier project phases already ran successfully in the user's local Next.js environment.

## Recommended first run

Start with a fresh local SQLite database. Register a new merchant and complete all six onboarding steps. Then run Buyer Demo, authorize a valid purchase, run Attack Lab scenarios, inspect Transaction Passport, simulate a failed payment and recovery in LOCAL_TEST, verify the Audit chain, and revisit Dashboard to see the actual generated telemetry.
