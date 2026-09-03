from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_merchant
from app.db.session import get_db
from app.models import Merchant, Product
from app.schemas.checkout import CheckoutProposalRequest, CheckoutProposalResponse
from app.services.intentlock import create_checkout_snapshot

router = APIRouter(tags=["agent-commerce"])


def _build_proposal(db: Session, merchant: Merchant, payload: CheckoutProposalRequest, require_discovery: bool) -> CheckoutProposalResponse:
    if require_discovery and not merchant.discovery_enabled:
        raise HTTPException(409, "Merchant agent discovery is not enabled")
    product = db.scalar(select(Product).where(Product.merchant_id == merchant.id, Product.sku == payload.sku, Product.visible.is_(True)))
    if product is None:
        raise HTTPException(404, "Visible SKU not found for this merchant")
    if product.inventory < payload.quantity:
        raise HTTPException(409, "Requested quantity exceeds merchant inventory")
    snapshot = create_checkout_snapshot(db, merchant, product.sku, payload.quantity)
    db.commit(); db.refresh(snapshot)
    return CheckoutProposalResponse(
        checkout_id=snapshot.id, merchant_id=merchant.id, merchant_name=merchant.name,
        sku=snapshot.sku, product=snapshot.product, brand=snapshot.brand, category=snapshot.category,
        variant=snapshot.variant, quantity=snapshot.quantity, unit_price_minor=snapshot.unit_price_minor,
        total_minor=snapshot.total_minor, currency=snapshot.currency, inventory_available=product.inventory,
        price_authority=snapshot.price_authority, checkout_hash=snapshot.checkout_hash, status="PROPOSED",
    )


@router.post("/agent-commerce/merchants/{merchant_id}/checkouts", response_model=CheckoutProposalResponse)
def public_checkout_proposal(merchant_id: str, payload: CheckoutProposalRequest, db: Session = Depends(get_db)) -> CheckoutProposalResponse:
    merchant = db.get(Merchant, merchant_id)
    if merchant is None:
        raise HTTPException(404, "Merchant not found")
    return _build_proposal(db, merchant, payload, require_discovery=True)


@router.post("/agent-commerce/checkouts", response_model=CheckoutProposalResponse)
def current_checkout_proposal(payload: CheckoutProposalRequest, merchant: Merchant = Depends(get_current_merchant), db: Session = Depends(get_db)) -> CheckoutProposalResponse:
    return _build_proposal(db, merchant, payload, require_discovery=False)
