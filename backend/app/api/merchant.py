from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_merchant
from app.db.session import get_db
from app.models import Merchant, MerchantPolicy
from app.schemas.merchant import MerchantResponse
from app.services.catalog import catalog_summary

router = APIRouter(tags=["merchant"])


@router.get("/merchant", response_model=MerchantResponse)
def get_merchant(
    merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db),
) -> MerchantResponse:
    policy = db.scalar(
        select(MerchantPolicy).where(
            MerchantPolicy.merchant_id == merchant.id,
            MerchantPolicy.status == "PUBLISHED",
        )
    )
    return MerchantResponse(
        merchant_id=merchant.id,
        merchant_name=merchant.name,
        environment=merchant.environment,
        status=merchant.status,
        onboarding_completed=merchant.onboarding_completed,
        payment_test_connected=merchant.payment_test_connected,
        discovery_enabled=merchant.discovery_enabled,
        identity_active=merchant.identity_active,
        identity_algorithm=merchant.identity_algorithm,
        identity_fingerprint=merchant.identity_fingerprint,
        policy_version=policy.version if policy else "none",
        policy_status=policy.status if policy else "NOT_PUBLISHED",
        catalog=catalog_summary(db, merchant.id),
    )
