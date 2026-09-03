import json
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import get_onboarded_merchant
from app.db.session import get_db
from app.models import CheckoutSnapshot, Intent, Mandate, Merchant, PaymentEvent, Product, RazorpayOrder, Transaction
from app.schemas.transactions import (
    AgentTransactionRequest, DemoExecuteRequest, IntentCompileRequest, IntentResponse,
    MandateCreateRequest, MandateResponse, PaymentSimulationRequest, TransactionResponse,
)
from app.services.agents import ensure_reference_agent
from app.services.intents import authorize_mandate, compile_intent
from app.services.intentlock import build_reference_envelope, create_checkout_snapshot, evaluate_transaction, transaction_checks
from app.services.payments import apply_payment_event

router = APIRouter(tags=["transactions"])


def serialize_tx(db: Session, tx: Transaction) -> TransactionResponse:
    snapshot = db.get(CheckoutSnapshot, tx.checkout_id)
    intent = db.get(Intent, tx.intent_id)
    mandate = db.get(Mandate, tx.mandate_id)
    order = db.scalar(select(RazorpayOrder).where(RazorpayOrder.transaction_id == tx.id))
    payment = db.scalar(select(PaymentEvent).where(PaymentEvent.transaction_id == tx.id).order_by(PaymentEvent.created_at.desc()).limit(1))
    product = db.scalar(select(Product).where(Product.merchant_id == tx.merchant_id, Product.sku == snapshot.sku)) if snapshot else None
    checks = transaction_checks(db, tx.id)
    return TransactionResponse(
        transaction_id=tx.id,
        intent_id=tx.intent_id,
        mandate_id=tx.mandate_id,
        agent_id=tx.agent_id,
        checkout_id=tx.checkout_id,
        sku=snapshot.sku if snapshot else "",
        product=snapshot.product if snapshot else "",
        quantity=snapshot.quantity if snapshot else 0,
        amount_minor=tx.amount_minor,
        currency=tx.currency,
        decision=tx.decision,
        payment_state=tx.payment_state,
        reason_codes=json.loads(tx.reason_codes_json or "[]"),
        latency_ms=tx.latency_ms,
        razorpay_api_calls=tx.razorpay_api_calls,
        duplicate_count=tx.duplicate_count,
        recovery_of_transaction_id=tx.recovery_of_transaction_id,
        created_at=tx.created_at,
        intent_text=intent.natural_language if intent else "",
        intent_brand=intent.brand if intent else None,
        intent_category=intent.category if intent else None,
        intent_max_amount_minor=intent.max_amount_minor if intent else 0,
        intent_max_quantity=intent.max_quantity if intent else 0,
        mandate_status=mandate.status if mandate else "",
        mandate_payload_hash=mandate.payload_hash if mandate else "",
        mandate_expires_at=mandate.expires_at if mandate else None,
        checkout_hash=snapshot.checkout_hash if snapshot else "",
        unit_price_minor=snapshot.unit_price_minor if snapshot else 0,
        price_authority=snapshot.price_authority if snapshot else "MERCHANT_CATALOG",
        payment_order_id=order.razorpay_order_id if order else None,
        payment_mode=order.mode if order else None,
        payment_id=payment.payment_id if payment else None,
        payment_signature_verified=payment.signature_verified if payment else None,
        inventory_after=product.inventory if product else None,
        checks=[{"name":c.check_name,"result":c.result,"reason_code":c.reason_code,"detail":c.detail} for c in checks],
    )


@router.post("/intents/compile", response_model=IntentResponse)
def compile_intent_api(payload: IntentCompileRequest, merchant: Merchant = Depends(get_onboarded_merchant), db: Session = Depends(get_db)):
    try:
        intent = compile_intent(db, merchant, payload.natural_language, sku=payload.sku, max_amount_minor=payload.max_amount_minor, max_quantity=payload.max_quantity)
        db.commit()
    except ValueError as exc:
        db.rollback(); raise HTTPException(409, str(exc)) from exc
    return IntentResponse(intent_id=intent.id,natural_language=intent.natural_language,brand=intent.brand,category=intent.category,max_amount_minor=intent.max_amount_minor,max_quantity=intent.max_quantity,allowed_variants=json.loads(intent.allowed_variants_json),status=intent.status)


@router.post("/mandates", response_model=MandateResponse)
def create_mandate_api(payload: MandateCreateRequest, merchant: Merchant = Depends(get_onboarded_merchant), db: Session = Depends(get_db)):
    intent = db.get(Intent, payload.intent_id)
    if intent is None or intent.merchant_id != merchant.id: raise HTTPException(404, "Intent not found")
    mandate = authorize_mandate(db, merchant, intent, agent_id=payload.agent_id, expires_minutes=payload.expires_minutes)
    db.commit()
    return MandateResponse(mandate_id=mandate.id,intent_id=mandate.intent_id,agent_id=mandate.agent_id,payload_hash=mandate.payload_hash,signature=mandate.signature,status=mandate.status,expires_at=mandate.expires_at)


@router.post("/transactions/evaluate", response_model=TransactionResponse)
def evaluate_api(payload: AgentTransactionRequest, merchant: Merchant = Depends(get_onboarded_merchant), db: Session = Depends(get_db)):
    intent = db.get(Intent, payload.intent_id); mandate = db.get(Mandate, payload.mandate_id)
    if intent is None or intent.merchant_id != merchant.id: raise HTTPException(404, "Intent not found")
    if mandate is None or mandate.merchant_id != merchant.id: raise HTTPException(404, "Mandate not found")
    try:
        tx = evaluate_transaction(
            db, merchant, intent=intent, mandate=mandate, sku=payload.sku, quantity=payload.quantity,
            checkout_id=payload.checkout_id, signed_checkout_hash=payload.checkout_hash,
            agent_id=payload.agent_id, nonce=payload.nonce, timestamp=payload.timestamp,
            signature=payload.signature, idempotency_key=payload.idempotency_key,
            asserted_total_minor=payload.asserted_total_minor,
        )
    except ValueError as exc:
        db.rollback(); raise HTTPException(409, str(exc)) from exc
    return serialize_tx(db, tx)


@router.post("/transactions/demo", response_model=TransactionResponse)
def demo_execute(payload: DemoExecuteRequest, merchant: Merchant = Depends(get_onboarded_merchant), db: Session = Depends(get_db)):
    product = db.scalar(select(Product).where(Product.merchant_id==merchant.id, Product.visible.is_(True), *( [Product.sku==payload.sku] if payload.sku else [] )).order_by(Product.price_minor.asc()))
    if product is None: raise HTTPException(409, "No visible product available")
    limit = payload.max_amount_minor or max(product.price_minor * payload.max_quantity, product.price_minor)
    natural = payload.natural_language or f"Buy up to {payload.max_quantity} {product.brand} {product.category} under ₹{limit//100:,}"
    intent = compile_intent(db, merchant, natural, sku=product.sku, max_amount_minor=limit, max_quantity=payload.max_quantity)
    mandate = authorize_mandate(db, merchant, intent)
    snapshot = create_checkout_snapshot(db, merchant, product.sku, payload.quantity)
    envelope = build_reference_envelope(db, merchant, mandate, snapshot)
    tx = evaluate_transaction(
        db, merchant, intent=intent, mandate=mandate, sku=product.sku, quantity=payload.quantity,
        checkout_id=snapshot.id, signed_checkout_hash=envelope["checkout_hash"],
        agent_id=envelope["agent_id"], nonce=envelope["nonce"], timestamp=envelope["timestamp"],
        signature=envelope["signature"], idempotency_key=f"demo_{uuid.uuid4().hex}",
    )
    if payload.payment_outcome and tx.decision == "ALLOW":
        order = db.scalar(select(RazorpayOrder).where(RazorpayOrder.transaction_id == tx.id))
        if order is not None and order.mode == "LOCAL_TEST":
            apply_payment_event(db, tx, payload.payment_outcome)
            db.commit(); db.refresh(tx)
    return serialize_tx(db, tx)


@router.get("/transactions", response_model=list[TransactionResponse])
def list_transactions(merchant: Merchant = Depends(get_onboarded_merchant), db: Session = Depends(get_db)):
    rows = db.scalars(select(Transaction).where(Transaction.merchant_id==merchant.id).order_by(Transaction.created_at.desc())).all()
    return [serialize_tx(db, tx) for tx in rows]


@router.get("/transactions/{transaction_id}", response_model=TransactionResponse)
def get_transaction(transaction_id: str, merchant: Merchant = Depends(get_onboarded_merchant), db: Session = Depends(get_db)):
    tx = db.get(Transaction, transaction_id)
    if tx is None or tx.merchant_id != merchant.id: raise HTTPException(404, "Transaction not found")
    return serialize_tx(db, tx)


@router.post("/transactions/{transaction_id}/payments/simulate", response_model=TransactionResponse)
def simulate_payment(transaction_id: str, payload: PaymentSimulationRequest, merchant: Merchant = Depends(get_onboarded_merchant), db: Session = Depends(get_db)):
    tx = db.get(Transaction, transaction_id)
    if tx is None or tx.merchant_id != merchant.id: raise HTTPException(404, "Transaction not found")
    if tx.decision != "ALLOW": raise HTTPException(409, "Blocked or step-up transactions cannot enter payment execution")
    order = db.scalar(select(RazorpayOrder).where(RazorpayOrder.transaction_id == tx.id))
    if order is None or order.mode != "LOCAL_TEST": raise HTTPException(409, "Payment simulation is available only in LOCAL_TEST mode")
    apply_payment_event(db, tx, payload.outcome, verified=False)
    db.commit(); db.refresh(tx)
    return serialize_tx(db, tx)


@router.post("/transactions/{transaction_id}/step-up/approve", response_model=TransactionResponse)
def approve_step_up(transaction_id: str, merchant: Merchant = Depends(get_onboarded_merchant), db: Session = Depends(get_db)):
    from datetime import UTC, datetime
    from sqlalchemy import func
    from app.models import PolicyDecision, RazorpayOrder
    from app.services.audit import append_audit
    from app.services.payments import create_order
    tx = db.get(Transaction, transaction_id)
    if tx is None or tx.merchant_id != merchant.id:
        raise HTTPException(404, "Transaction not found")
    if tx.decision != "STEP-UP":
        raise HTTPException(409, "Transaction is not awaiting step-up approval")
    checks = transaction_checks(db, tx.id)
    if any(c.result == "FAIL" for c in checks):
        raise HTTPException(409, "A transaction with failed controls cannot be step-up approved")
    mandate = db.get(Mandate, tx.mandate_id)
    if mandate is None:
        raise HTTPException(409, "Mandate evidence missing")
    expires = mandate.expires_at.replace(tzinfo=UTC) if mandate.expires_at.tzinfo is None else mandate.expires_at.astimezone(UTC)
    if expires <= datetime.now(UTC):
        raise HTTPException(409, "Mandate expired before step-up approval")
    existing_order = db.scalar(select(RazorpayOrder).where(RazorpayOrder.transaction_id == tx.id))
    if existing_order is not None:
        raise HTTPException(409, "Payment order already exists")
    sequence = (db.scalar(select(func.max(PolicyDecision.sequence)).where(PolicyDecision.transaction_id == tx.id)) or 0) + 1
    db.add(PolicyDecision(transaction_id=tx.id, check_name="Human Step-Up Approval", result="PASS", detail="Authenticated merchant operator approved the step-up", sequence=sequence))
    tx.decision = "ALLOW"
    mandate.status = "CONSUMED"
    mandate.consumed_at = datetime.now(UTC)
    append_audit(db, merchant.id, "STEP_UP_APPROVED", {"transaction_id": tx.id, "approved_by": "authenticated_merchant_operator"}, transaction_id=tx.id, actor="human-step-up")
    create_order(db, tx)
    db.commit(); db.refresh(tx)
    return serialize_tx(db, tx)

@router.post("/agent-commerce/merchants/{merchant_id}/transactions", response_model=TransactionResponse)
def public_agent_transaction(merchant_id: str, payload: AgentTransactionRequest, db: Session = Depends(get_db)):
    merchant = db.get(Merchant, merchant_id)
    if merchant is None:
        raise HTTPException(404, "Merchant not found")
    if not merchant.discovery_enabled or not merchant.onboarding_completed:
        raise HTTPException(409, "Merchant is not currently AI-transactable")
    intent = db.get(Intent, payload.intent_id)
    mandate = db.get(Mandate, payload.mandate_id)
    if intent is None or intent.merchant_id != merchant.id:
        raise HTTPException(404, "Intent not found")
    if mandate is None or mandate.merchant_id != merchant.id:
        raise HTTPException(404, "Mandate not found")
    try:
        tx = evaluate_transaction(
            db, merchant, intent=intent, mandate=mandate, sku=payload.sku,
            quantity=payload.quantity, agent_id=payload.agent_id, nonce=payload.nonce,
            timestamp=payload.timestamp, signature=payload.signature,
            idempotency_key=payload.idempotency_key,
            checkout_id=payload.checkout_id, signed_checkout_hash=payload.checkout_hash,
            asserted_total_minor=payload.asserted_total_minor,
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(409, str(exc)) from exc
    return serialize_tx(db, tx)
