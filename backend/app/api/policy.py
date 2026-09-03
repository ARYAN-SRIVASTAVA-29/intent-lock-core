from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_merchant, get_onboarded_merchant
from app.db.session import get_db
from app.models import Merchant, MerchantPolicy
from app.schemas.policy import PolicyResponse, PolicyUpdateRequest
from app.services.seed import seed_policy_for_merchant

router = APIRouter(tags=["policy"])


def _get(db: Session, merchant_id: str) -> MerchantPolicy:
    policy = db.scalar(
        select(MerchantPolicy).where(
            MerchantPolicy.merchant_id == merchant_id,
            MerchantPolicy.status == "PUBLISHED",
        )
    )
    if not policy:
        raise HTTPException(404, "Published policy not found")
    return policy


def _apply(policy: MerchantPolicy, payload: PolicyUpdateRequest) -> None:
    policy.max_transaction_minor = payload.max_transaction_minor
    policy.step_up_above_minor = payload.step_up_above_minor
    policy.daily_spend_minor = payload.daily_spend_minor
    policy.max_discount_pct = payload.max_discount_pct
    policy.max_recovery_attempts = payload.max_recovery_attempts
    policy.alternative_skus_allowed = payload.alternative_skus_allowed
    policy.merchant_switching_allowed = payload.merchant_switching_allowed
    policy.unknown_agent_action = payload.unknown_agent_action.upper()
    policy.status = "PUBLISHED"


@router.get("/policies/current", response_model=PolicyResponse)
def current(
    merchant: Merchant = Depends(get_onboarded_merchant),
    db: Session = Depends(get_db),
):
    return _get(db, merchant.id)


@router.put("/policies/current", response_model=PolicyResponse)
def update_current(
    payload: PolicyUpdateRequest,
    merchant: Merchant = Depends(get_onboarded_merchant),
    db: Session = Depends(get_db),
):
    policy = _get(db, merchant.id)
    _apply(policy, payload)
    db.commit()
    db.refresh(policy)
    return policy


@router.post("/onboarding/policy/publish", response_model=PolicyResponse)
def publish(
    merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db),
):
    policy = seed_policy_for_merchant(db, merchant.id)
    db.commit()
    db.refresh(policy)
    return policy


@router.get("/agent-commerce/merchants/{merchant_id}/policy", response_model=PolicyResponse)
def public_policy(merchant_id: str, db: Session = Depends(get_db)):
    merchant = db.get(Merchant, merchant_id)
    if merchant is None:
        raise HTTPException(404, "Merchant not found")
    if not merchant.discovery_enabled:
        raise HTTPException(409, "Merchant agent discovery is not enabled")
    return _get(db, merchant_id)
