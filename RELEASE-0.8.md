# IntentLock 0.8 — Demo Hardening Release

This release keeps the approved landing page and six-step onboarding unchanged while upgrading the authenticated Merchant Console and the core hackathon demonstrations.

## Merchant Console

- Replaced the card-heavy dashboard with a compact operations console.
- Added a permanent **Reference Buyer** navigation item near the top of Commerce.
- Added a dedicated **Payment Setup** page with live mode, credential and webhook readiness.
- Consolidated repeated dashboard telemetry into one readiness bar, four decision-grade metrics, recent economic actions, authority decisions, and operational health.
- All values remain API/database-derived; no fake console telemetry was added.

## Reference Buyer 2.0

- Broad requests return up to 12 eligible live-catalog matches instead of one product.
- Results include price, inventory, delivery, fit score, recommendation label and comparison evidence.
- The user selects the exact SKU before creating the human mandate.
- Merchant catalog remains authoritative for price.
- ALLOW is still required before either local payment simulation or Razorpay Checkout.

## Interactive Attack Lab 2.0

- Presets now populate an editable malicious payload.
- Product, quantity, asserted total, merchant, checkout tampering, forged signature and mandate expiry are editable.
- Added `Custom Payload` mode.
- Results show all deterministic checks, failure reason codes, latency and Razorpay calls.
- Duplicate Invocation still proves three requests produce one economic action.

## Recovery 2.0

- Each failed payment exposes candidate products scored against the original brand, category, variant, amount, inventory and quantity authority.
- Ineligible alternatives are explicitly marked with reason codes.
- Recovery re-enters the same IntentLock kernel.
- LOCAL_TEST recoveries complete locally; RAZORPAY_TEST recoveries wait for real verified Checkout/webhook evidence.

## Razorpay Test Mode hardening

- Included a ready-to-fill `backend/.env` without secrets.
- Only `rzp_test_...` keys are accepted by the demo payment orchestrator.
- Payment configuration reports connected/incomplete/invalid/local states without exposing the Key Secret.
- Checkout and webhook readiness are separate.
- Checkout signatures, webhook signatures, amount, currency and state transitions remain verified server-side.
- Added handling for `order.paid` as captured evidence.

## Security and verification

- Added deterministic variant enforcement to the mandate kernel.
- Backend suite expanded from 34 to **38 passing tests**.
- Production Next.js build and strict TypeScript check pass.
