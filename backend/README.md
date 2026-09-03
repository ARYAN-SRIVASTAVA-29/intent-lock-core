# IntentLock API — Merchant Control Room Release 0.9.1

FastAPI backend for the IntentLock agentic-commerce trust boundary.

See `../PHASE5-7.md` for the complete feature list and walkthrough.

## Quick start

```powershell
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Swagger: `http://localhost:8000/docs`

Default database: local SQLite (`intentlock.db`). Set `DATABASE_URL` for PostgreSQL.

Default payment mode: `LOCAL_TEST`. Configure Razorpay Test Mode credentials in `.env` to use actual Razorpay Test Orders/Checkout/webhooks.

Successful payment authorization/capture now commits catalog inventory exactly once. A later verified failure releases the committed quantity, and every mutation is added to the audit chain.

See `../RAZORPAY-TEST-MODE.md` for the exact Test Mode activation steps.

## Security boundary

The AI/agent proposes an SKU and quantity. Merchant data determines price. The agent signs the concrete checkout hash. IntentLock verifies signed human authority, agent identity, checkout integrity, merchant policy, replay/idempotency and recovery lineage before payment execution.
