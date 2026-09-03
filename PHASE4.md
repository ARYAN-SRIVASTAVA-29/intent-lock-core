# IntentLock Phase 4 — Merchant Control Plane Becomes Real

Phase 4 includes the Phase 3 onboarding-flow correction and moves merchant enablement off frontend placeholders.

## What is real in Phase 4

- Authenticated merchant identity and ownership from Phase 3.
- Required onboarding actions cannot be skipped silently.
- Inline onboarding errors replace unhandled Next.js errors.
- Merchant store name and merchant ID come from the authenticated backend account.
- CSV/JSON catalog upload is persisted per merchant.
- Demo Catalog is a real seeded dataset: 24 distinct products / 31 SKU rows.
- Uploaded catalog summary is computed from the merchant database and reused by onboarding, Catalog, discovery, readiness, and Dashboard catalog modules.
- Catalog freshness comes from the latest product `updated_at` timestamp.
- Ed25519 merchant identity fingerprint shown by onboarding is the generated backend value.
- Published policy is persisted and can be edited from `/policies` through `PUT /api/v1/policies/current`.
- Public agent catalog/policy are exposed only after agent discovery is enabled.
- Agent discovery advertises a real checkout-proposal endpoint.
- Checkout proposals use merchant catalog price as authority; the agent supplies SKU + quantity, not authoritative price.
- Merchant Console remains locked until onboarding is completed.

## Still demo telemetry (intentionally)

The transaction security engine is the next phase. Until then, these UI areas remain demo telemetry:

- Agent-driven GMV and economic-action counts.
- Agent registry counts.
- ALLOW/BLOCK/STEP-UP transaction history.
- Replay/idempotency enforcement counts.
- Razorpay orders/payments/webhooks.
- Recovery and recovered GMV.
- Audit hash-chain events and Transaction Passport evidence.

They will become real only as their backend systems are implemented. Phase 4 does not pretend those systems already exist.

## Important endpoints

### Merchant control plane

- `GET /api/v1/merchant`
- `GET /api/v1/catalog/products`
- `POST /api/v1/catalog/demo`
- `POST /api/v1/catalog/upload`
- `GET /api/v1/policies/current`
- `PUT /api/v1/policies/current`
- `GET /api/v1/onboarding/readiness`

### Agent-facing commerce surface

- `GET /api/v1/agent-commerce/merchants/{merchant_id}/discovery`
- `GET /api/v1/agent-commerce/merchants/{merchant_id}/catalog`
- `GET /api/v1/agent-commerce/merchants/{merchant_id}/policy`
- `POST /api/v1/agent-commerce/merchants/{merchant_id}/checkouts`

Checkout request example:

```json
{
  "sku": "SONY-XM5-BLK",
  "quantity": 1
}
```

The backend calculates unit price and total from the merchant catalog and returns `price_authority = MERCHANT_CATALOG`.

## Local verification

Backend tests:

```powershell
cd backend
pytest -q
```

Expected Phase 4 result: `12 passed`.

For an easy real-count check, upload `examples/catalog-4-products.csv`. The merchant should show 4 products / 4 SKUs / 3 brands / 2 categories across onboarding, Catalog, discovery, readiness, and the Dashboard catalog modules.
