from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models import (  # noqa: F401
    Agent, AgentNonce, AuditEvent, CheckoutSnapshot, Intent, Mandate, Merchant, MerchantPolicy,
    PaymentEvent, PolicyDecision, Product, RazorpayOrder, RecoveryCase, Transaction, User,
)
from app.services.seed import seed_demo_data

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_demo_data(db)
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.9.1",
    description="IntentLock control plane for safe agentic commerce.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_prefix)


@app.get("/", tags=["system"])
def root() -> dict[str, str]:
    return {
        "service": "intentlock",
        "status": "online",
        "version": "0.9.1",
        "docs": "/docs",
    }
