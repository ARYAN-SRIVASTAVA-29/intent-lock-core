# IntentLock 0.9.1 — Session Exit Patch

This patch adds a permanent **Log out** control to the authenticated merchant console without changing the approved landing page, onboarding, dashboard, Reference Buyer, Attack Lab, or enforcement architecture.

## Logout behavior

- The control is available at the bottom of the merchant sidebar on every console route.
- It calls the existing FastAPI logout endpoint, which deletes the HttpOnly session cookie.
- After the server confirms logout, the browser performs a full navigation to the IntentLock landing page.
- The button exposes pending and retry states so a failed API request is not presented as a completed logout.

## Firewall boundary

IntentLock remains a pre-payment enforcement gateway, not merely a maximum-spend settings page. The kernel verifies agent identity and signature, request freshness and nonce replay, signed human authority, mandate binding and expiry, merchant/payee identity, checkout-to-request binding, SKU attributes, quantity, inventory, merchant-authoritative price, checkout integrity, merchant limits, daily velocity, step-up thresholds, idempotency, and recovery lineage before it may create a Razorpay order.
