# Phase 3 onboarding guard fix

This patch preserves the approved onboarding UI while fixing the Phase 3 activation UX:

- Payment must be tested before Step 1 can advance.
- A demo/CSV/JSON catalog must be loaded before Step 2 can advance.
- Step 3 publishes the default policy on Continue.
- Step 4 provisions the Ed25519 merchant identity on Continue.
- Agent discovery must pass before Step 5 can advance.
- Step 6 reads the real backend readiness state instead of displaying hard-coded PASS values.
- Enter Merchant Console stays disabled until the backend reports AI_TRANSACTABLE.
- API failures are displayed inline instead of causing an unhandled Next.js development error indicator.
- Existing completed backend state is restored when onboarding is reloaded.
