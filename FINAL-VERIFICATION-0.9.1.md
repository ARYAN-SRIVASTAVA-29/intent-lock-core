# IntentLock 0.9.1 verification

- Server logout deletes the HttpOnly merchant session cookie.
- A logged-out session can no longer access `/api/v1/auth/me`.
- Console logout waits for server confirmation, then returns to `/` with a full-page navigation.
- Failed logout requests remain visible and retryable.
- Existing firewall, inventory, payment, dashboard, landing-page, and onboarding behavior is unchanged.
- Backend regression suite: `39 passed`.
- Strict TypeScript validation passed.
- Production Next.js build passed.
