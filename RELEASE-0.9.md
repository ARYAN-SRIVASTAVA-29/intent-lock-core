# IntentLock 0.9 — Merchant Control Room Release

This release keeps the approved landing page and six-step onboarding unchanged. It corrects the authenticated console layout, adds payment-aware inventory operations, and expands the dashboard into a real merchant control room.

## Inventory lifecycle

- Successful `AUTHORIZED`, `CAPTURED`, and recovered payments commit the purchased SKU quantity.
- Razorpay retries and `AUTHORIZED → CAPTURED` transitions are idempotent and cannot deduct stock twice.
- An authorized payment that later fails releases its committed inventory exactly once.
- Inventory commits and releases are recorded in the hash-linked audit ledger.
- Reference Buyer and Transaction Passport show remaining inventory after payment.

## Console navigation repair

- Corrected the CSS boundary that mistakenly promoted nested Buyer, Attack Lab, and Recovery panels into the fixed application sidebar.
- The permanent merchant navigation now remains present on every console route.
- The IntentLock logo, Merchant Console breadcrumb, and Control room action all return to Dashboard.
- Responsive navigation continues to use the existing mobile drawer.

## Reference Buyer workspace

- Rebuilt as a dense catalog-results and authorization workspace.
- Added payment rail state, exact available inventory, inventory-commit confirmation, and a direct Control room route.
- Search, authorization, payment, transaction evidence, and recovery actions remain connected to the real FastAPI backend.

## Attack Lab workspace

- Restored the full-width console layout with a dedicated preset rail.
- Expanded the authority-versus-agent comparison, editable fields, tamper controls, execution state, and evidence matrix.
- All results remain persisted kernel decisions; blocked attacks make zero Razorpay calls.

## Merchant control room

- Added a merchant-specific welcome header.
- Expanded from a short dashboard into a scrollable operations surface with six primary KPIs.
- Added seven-day action activity, commerce funnel, inventory intelligence, top product activity, live audit stream, payment readiness, recovery state, and platform health.
- All analytics are computed from merchant transactions, catalog inventory, payment orders, agent records, and audit events. No fake telemetry was added.

## Loading and verification

- Added route-level loading and data skeletons.
- Added visible progress states for Buyer and Attack Lab execution.
- Backend suite: 39 passing tests.
- Strict TypeScript validation and the production Next.js build pass.
