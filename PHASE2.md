# IntentLock Phase 2 — Merchant Commerce Foundation

This phase converts the first frontend surfaces from pure mock data to a real FastAPI + SQLAlchemy commerce backend.

## What is real now

1. `Demo Audio Store` exists as a persisted merchant record.
2. The demo catalog is persisted: **24 products / 31 SKUs / 6 brands / 4 categories**.
3. Prices are stored in **minor units** and returned by the server as authoritative commercial data.
4. `GET /api/v1/catalog/products` serves the Merchant Console Catalog page.
5. `GET /api/v1/agent-commerce/catalog` exposes only agent-visible SKUs.
6. `GET /api/v1/agent-commerce/discovery` advertises the merchant's machine-readable commerce capabilities.
7. `POST /api/v1/agent-commerce/discovery/test` performs a real discovery preflight.
8. `GET /api/v1/policies/current` exposes published merchant policy v1.
9. `GET /api/v1/onboarding/readiness` derives readiness from real backend state.
10. The frontend Catalog page calls FastAPI. It falls back to demo data only if the backend is offline.
11. Onboarding Step 5's **Run discovery test** button now calls the real FastAPI discovery endpoints.

## Why this matters

The merchant is no longer called "AI-transactable" only because the UI says so. A compatible agent can request the discovery document, find the agent-readable catalog and policy endpoint, and obtain authoritative product data.

This is the enablement side of IntentLock. The next phase adds the enforcement side:

`buyer intent -> bounded human mandate -> authoritative checkout -> deterministic IntentLock decision`.
