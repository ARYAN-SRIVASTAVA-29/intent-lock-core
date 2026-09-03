import hashlib
import hmac
import json
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import AuditEvent, CheckoutSnapshot, PaymentEvent, Product, RazorpayOrder, RecoveryCase, Transaction
from app.services.audit import append_audit

settings = get_settings()


def _inventory_audit_exists(db: Session, tx: Transaction, event_type: str) -> bool:
    return db.scalar(
        select(AuditEvent.id).where(
            AuditEvent.transaction_id == tx.id,
            AuditEvent.event_type == event_type,
        ).limit(1)
    ) is not None


def _commit_inventory(db: Session, tx: Transaction, outcome: str) -> None:
    """Commit catalog inventory exactly once when payment becomes successful.

    Razorpay can send AUTHORIZED followed by CAPTURED and may retry either
    event. The audit marker makes the stock mutation idempotent across all of
    those deliveries without requiring a schema migration for existing demos.
    """
    if _inventory_audit_exists(db, tx, "INVENTORY_COMMITTED"):
        return
    snapshot = db.get(CheckoutSnapshot, tx.checkout_id)
    if snapshot is None:
        raise ValueError("Checkout evidence missing for inventory commit")
    product = db.scalar(
        select(Product).where(
            Product.merchant_id == tx.merchant_id,
            Product.sku == snapshot.sku,
        )
    )
    if product is None:
        raise ValueError("Catalog product missing for inventory commit")
    if product.inventory < snapshot.quantity:
        raise ValueError(
            f"Inventory changed before payment completed: requested {snapshot.quantity}; available {product.inventory}"
        )
    before = product.inventory
    product.inventory -= snapshot.quantity
    append_audit(
        db,
        tx.merchant_id,
        "INVENTORY_COMMITTED",
        {
            "transaction_id": tx.id,
            "sku": snapshot.sku,
            "quantity": snapshot.quantity,
            "inventory_before": before,
            "inventory_after": product.inventory,
            "payment_state": outcome,
        },
        transaction_id=tx.id,
        actor="inventory-ledger",
    )


def _release_inventory(db: Session, tx: Transaction) -> None:
    """Return committed stock once if an authorized payment later fails."""
    if not _inventory_audit_exists(db, tx, "INVENTORY_COMMITTED"):
        return
    if _inventory_audit_exists(db, tx, "INVENTORY_RELEASED"):
        return
    snapshot = db.get(CheckoutSnapshot, tx.checkout_id)
    if snapshot is None:
        return
    product = db.scalar(
        select(Product).where(
            Product.merchant_id == tx.merchant_id,
            Product.sku == snapshot.sku,
        )
    )
    if product is None:
        return
    before = product.inventory
    product.inventory += snapshot.quantity
    append_audit(
        db,
        tx.merchant_id,
        "INVENTORY_RELEASED",
        {
            "transaction_id": tx.id,
            "sku": snapshot.sku,
            "quantity": snapshot.quantity,
            "inventory_before": before,
            "inventory_after": product.inventory,
            "payment_state": "FAILED",
        },
        transaction_id=tx.id,
        actor="inventory-ledger",
    )


def create_order(db: Session, tx: Transaction) -> RazorpayOrder:
    if tx.decision != "ALLOW":
        raise ValueError("Only ALLOW transactions may create payment orders")

    existing = db.scalar(select(RazorpayOrder).where(RazorpayOrder.transaction_id == tx.id))
    if existing is not None:
        return existing

    if settings.razorpay_key_id and settings.razorpay_key_secret:
        if not settings.razorpay_key_id.startswith("rzp_test_"):
            raise ValueError("IntentLock demo accepts Razorpay Test Mode keys only (rzp_test_...)")
        import razorpay

        client = razorpay.Client(auth=(settings.razorpay_key_id, settings.razorpay_key_secret))
        data = client.order.create(
            {"amount": tx.amount_minor, "currency": tx.currency, "receipt": tx.id}
        )
        order_id = data["id"]
        mode = "RAZORPAY_TEST"
    else:
        order_id = f"order_test_{uuid.uuid4().hex[:14]}"
        mode = "LOCAL_TEST"

    order = RazorpayOrder(
        transaction_id=tx.id,
        razorpay_order_id=order_id,
        amount_minor=tx.amount_minor,
        currency=tx.currency,
        status="CREATED",
        mode=mode,
    )
    db.add(order)
    tx.razorpay_api_calls = 1 if mode == "RAZORPAY_TEST" else 0
    tx.payment_state = "ORDER_CREATED"
    db.flush()
    append_audit(
        db,
        tx.merchant_id,
        "RAZORPAY_ORDER_CREATED" if mode == "RAZORPAY_TEST" else "LOCAL_TEST_ORDER_CREATED",
        {
            "transaction_id": tx.id,
            "payment_order_id": order_id,
            "amount_minor": tx.amount_minor,
            "mode": mode,
        },
        transaction_id=tx.id,
        actor="payment-orchestrator",
    )
    return order


_ALLOWED_TRANSITIONS = {
    "ORDER_CREATED": {"AUTHORIZED", "CAPTURED", "FAILED"},
    "AUTHORIZED": {"AUTHORIZED", "CAPTURED", "FAILED"},
    "CAPTURED": {"CAPTURED"},
    "FAILED": {"FAILED"},
    "RECOVERED": {"RECOVERED"},
}


def apply_payment_event(
    db: Session,
    tx: Transaction,
    outcome: str,
    payment_id: str | None = None,
    *,
    verified: bool = True,
) -> PaymentEvent:
    """Apply one authoritative payment state transition.

    Repeated delivery of the same event is idempotent. State regressions such
    as CAPTURED -> FAILED/AUTHORIZED are rejected.
    """
    outcome = outcome.upper()
    mapping = {
        "CAPTURED": "payment.captured",
        "FAILED": "payment.failed",
        "AUTHORIZED": "payment.authorized",
    }
    if outcome not in mapping:
        raise ValueError("Unsupported payment outcome")

    current = tx.payment_state
    if current == "RECOVERED" and outcome == "CAPTURED":
        existing = db.scalar(
            select(PaymentEvent)
            .where(
                PaymentEvent.transaction_id == tx.id,
                PaymentEvent.event_type == "payment.captured",
            )
            .order_by(PaymentEvent.created_at.desc())
        )
        if existing is not None:
            return existing
    if current not in _ALLOWED_TRANSITIONS:
        raise ValueError(f"Payment event cannot be applied from state {current}")
    if outcome not in _ALLOWED_TRANSITIONS[current]:
        raise ValueError(f"Invalid payment state transition {current} -> {outcome}")

    # Razorpay may retry webhooks. Do not produce duplicate economic evidence.
    if current == outcome:
        existing = db.scalar(
            select(PaymentEvent)
            .where(
                PaymentEvent.transaction_id == tx.id,
                PaymentEvent.event_type == mapping[outcome],
            )
            .order_by(PaymentEvent.created_at.desc())
        )
        if existing is not None:
            return existing

    if outcome in {"AUTHORIZED", "CAPTURED"}:
        _commit_inventory(db, tx, outcome)
    elif outcome == "FAILED":
        _release_inventory(db, tx)

    tx.payment_state = outcome
    order = db.scalar(select(RazorpayOrder).where(RazorpayOrder.transaction_id == tx.id))
    if order is not None:
        order.status = outcome

    event = PaymentEvent(
        transaction_id=tx.id,
        event_type=mapping[outcome],
        payment_id=payment_id or f"pay_test_{uuid.uuid4().hex[:14]}",
        signature_verified=verified,
        payload_json=json.dumps({"outcome": outcome}),
    )
    db.add(event)
    db.flush()

    if outcome == "FAILED":
        existing_case = db.scalar(
            select(RecoveryCase).where(RecoveryCase.original_transaction_id == tx.id)
        )
        if existing_case is None:
            db.add(
                RecoveryCase(
                    id=f"RCV-{uuid.uuid4().hex[:8].upper()}",
                    merchant_id=tx.merchant_id,
                    original_transaction_id=tx.id,
                    status="OPEN",
                )
            )
            db.flush()

    if outcome == "CAPTURED" and tx.recovery_of_transaction_id:
        recovery_case = db.scalar(
            select(RecoveryCase).where(
                RecoveryCase.original_transaction_id == tx.recovery_of_transaction_id
            )
        )
        if recovery_case is not None:
            recovery_case.status = "RECOVERED"
            recovery_case.recovered_transaction_id = tx.id
            recovery_case.last_reason = "Recovered inside original human authority"
            tx.payment_state = "RECOVERED"

    append_audit(
        db,
        tx.merchant_id,
        mapping[outcome].upper().replace(".", "_"),
        {
            "transaction_id": tx.id,
            "payment_id": event.payment_id,
            "signature_verified": verified,
            "state": tx.payment_state,
        },
        transaction_id=tx.id,
        actor="razorpay-webhook" if verified else "local-test-simulator",
    )
    return event


def verify_checkout_signature(order_id: str, payment_id: str, signature: str) -> bool:
    if not settings.razorpay_key_secret:
        return False
    message = f"{order_id}|{payment_id}".encode()
    expected = hmac.new(settings.razorpay_key_secret.encode(), message, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
