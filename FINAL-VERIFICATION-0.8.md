# IntentLock 0.8 — Final Verification

## Passed

- Backend automated suite: **38 / 38 tests passing**.
- Backend Python source compilation: passed.
- Strict TypeScript check: passed.
- Next.js optimized production build: passed.
- Landing page source: unchanged.
- Six-step onboarding source: unchanged.
- Console operational metrics remain API/database-derived.
- Razorpay Key Secret is never returned by the API or embedded in frontend code.
- No account credentials or real API secrets are included.

## New release-critical tests

- Broad Buyer request returns multiple ranked, eligible products.
- Buyer recommendation remains advisory and exact SKU selection is explicit.
- Editable custom attack payload runs through the real kernel and is blocked before Razorpay.
- Recovery API returns eligible and ineligible alternatives with authority reason codes.
- Payment configuration explicitly reports LOCAL_TEST when account keys are absent.
- Original 34 transaction, replay, idempotency, recovery, audit, auth, catalog and discovery tests remain passing.

## Razorpay network boundary

The real order/Checkout path requires the merchant's own free Razorpay Test Mode Key ID and Key Secret. Those credentials cannot be bundled publicly. Paste them into `backend/.env`, restart FastAPI, and follow `RAZORPAY-TEST-MODE.md`.

Webhook completion requires a publicly reachable HTTPS backend. Local Checkout signature verification works after adding Test keys; final captured state is completed from verified Razorpay webhook evidence when webhook delivery is available.
