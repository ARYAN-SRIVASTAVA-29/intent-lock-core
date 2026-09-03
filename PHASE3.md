# IntentLock Phase 3 — Merchant Authentication & Ownership

Phase 3 preserves the approved console/onboarding layout while adding real merchant accounts and server-side access control.

## What is real now
- Register with store name + email + password.
- Login/logout/me using an HttpOnly signed session cookie.
- Passwords stored with PBKDF2-SHA256 + random salt (never plaintext).
- One authenticated owner is bound to one merchant for the hackathon MVP.
- Merchant Console routes are client-gated; private FastAPI endpoints are also server-protected.
- Incomplete merchants are redirected to `/onboard`; completed merchants may enter `/dashboard`.
- New merchants have isolated catalogs/policies/readiness state.
- Onboarding payment test, demo catalog, CSV/JSON catalog upload, policy publish, Ed25519 merchant identity provisioning, discovery test and final activation call real FastAPI endpoints.
- Public agent discovery/catalog endpoints are merchant-specific, while private control-plane endpoints require merchant authentication.

## Run
Frontend: `npm install` then `npm run dev`.
Backend: create/activate `.venv`, `pip install -r requirements.txt`, then `uvicorn app.main:app --reload --port 8000`.

Use a fresh Phase 3 folder/database. `AUTH_SECRET` in `.env` should be changed before any public deployment.
