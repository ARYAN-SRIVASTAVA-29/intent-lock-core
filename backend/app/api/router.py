from fastapi import APIRouter
from app.api.auth import router as auth_router
from app.api.catalog import router as catalog_router
from app.api.checkout import router as checkout_router
from app.api.discovery import router as discovery_router
from app.api.health import router as health_router
from app.api.merchant import router as merchant_router
from app.api.policy import router as policy_router
from app.api.readiness import router as readiness_router
from app.api.transactions import router as transactions_router
from app.api.agents import router as agents_router
from app.api.payments import router as payments_router
from app.api.recovery import router as recovery_router
from app.api.audit import router as audit_router
from app.api.attack import router as attack_router
from app.api.dashboard import router as dashboard_router
from app.api.buyer import router as buyer_router
api_router=APIRouter()
for r in [health_router,auth_router,merchant_router,catalog_router,checkout_router,policy_router,discovery_router,readiness_router,transactions_router,agents_router,payments_router,recovery_router,audit_router,attack_router,dashboard_router,buyer_router]: api_router.include_router(r)
