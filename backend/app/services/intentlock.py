import json
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Agent,
    AgentNonce,
    CheckoutSnapshot,
    Intent,
    Mandate,
    Merchant,
    MerchantPolicy,
    PolicyDecision,
    Product,
    Transaction,
)
from app.services.agents import ensure_reference_agent
from app.services.audit import append_audit
from app.services.crypto import canonical_json, sha256_text, sign_text, verify_text
from app.services.payments import create_order


@dataclass
class Check:
    name: str
    result: str
    reason_code: str | None = None
    detail: str = ""


def _aware(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def current_policy(db: Session, merchant_id: str) -> MerchantPolicy:
    policy = db.scalar(
        select(MerchantPolicy)
        .where(MerchantPolicy.merchant_id == merchant_id, MerchantPolicy.status == "PUBLISHED")
        .order_by(MerchantPolicy.published_at.desc())
    )
    if policy is None:
        raise ValueError("Published merchant policy not found")
    return policy


def create_checkout_snapshot(db: Session, merchant: Merchant, sku: str, quantity: int) -> CheckoutSnapshot:
    product = db.scalar(
        select(Product).where(
            Product.merchant_id == merchant.id,
            Product.sku == sku,
            Product.visible.is_(True),
        )
    )
    if product is None:
        raise ValueError("Visible SKU not found for this merchant")
    if quantity < 1:
        raise ValueError("Quantity must be at least 1")

    total = product.price_minor * quantity
    payload = {
        "merchant_id": merchant.id,
        "sku": product.sku,
        "product": product.product,
        "brand": product.brand,
        "category": product.category,
        "variant": product.variant,
        "quantity": quantity,
        "unit_price_minor": product.price_minor,
        "total_minor": total,
        "currency": product.currency,
        "price_authority": "MERCHANT_CATALOG",
    }
    canonical = canonical_json(payload)
    snapshot = CheckoutSnapshot(
        id=f"CHK-{uuid.uuid4().hex[:10].upper()}",
        merchant_id=merchant.id,
        sku=product.sku,
        product=product.product,
        brand=product.brand,
        category=product.category,
        variant=product.variant,
        quantity=quantity,
        unit_price_minor=product.price_minor,
        total_minor=total,
        currency=product.currency,
        canonical_payload=canonical,
        checkout_hash=sha256_text(canonical),
        price_authority="MERCHANT_CATALOG",
    )
    db.add(snapshot)
    db.flush()
    return snapshot


def build_reference_envelope(
    db: Session,
    merchant: Merchant,
    mandate: Mandate,
    snapshot: CheckoutSnapshot,
    *,
    nonce: str | None = None,
    timestamp: int | None = None,
    checkout_hash_override: str | None = None,
) -> dict[str, Any]:
    """Build the exact signed request used by the reference buyer.

    The signature binds the agent to the mandate, concrete checkout snapshot,
    SKU/quantity, nonce, and timestamp.  A checkout-hash override is useful for
    Attack Lab because it lets us sign a deliberately mutated checkout rather
    than merely corrupting a signature after the fact.
    """
    agent = ensure_reference_agent(db, merchant.id)
    nonce = nonce or f"an_{uuid.uuid4().hex}"
    timestamp = timestamp or int(time.time())
    body = {
        "agent_id": agent.agent_id,
        "mandate_id": mandate.id,
        "sku": snapshot.sku,
        "quantity": snapshot.quantity,
        "checkout_id": snapshot.id,
        "checkout_hash": checkout_hash_override or snapshot.checkout_hash,
        "nonce": nonce,
        "timestamp": timestamp,
    }
    canonical = canonical_json(body)
    if not agent.demo_private_key:
        raise ValueError("Reference agent signing key unavailable")
    return {**body, "signature": sign_text(agent.demo_private_key, canonical)}


def evaluate_transaction(
    db: Session,
    merchant: Merchant,
    *,
    intent: Intent,
    mandate: Mandate,
    sku: str,
    quantity: int,
    checkout_id: str,
    signed_checkout_hash: str,
    agent_id: str,
    nonce: str,
    timestamp: int,
    signature: str,
    idempotency_key: str,
    asserted_total_minor: int | None = None,
    merchant_override: str | None = None,
    recovery_of_transaction_id: str | None = None,
    create_payment: bool = True,
) -> Transaction:
    # Idempotency must be checked before replay detection. Repeated delivery of
    # the same economic action returns the existing action instead of creating
    # a second transaction/order.
    existing = db.scalar(
        select(Transaction).where(
            Transaction.merchant_id == merchant.id,
            Transaction.idempotency_key == idempotency_key,
        )
    )
    if existing is not None:
        existing.duplicate_count += 1
        append_audit(
            db,
            merchant.id,
            "DUPLICATE_INVOCATION_DEDUPLICATED",
            {
                "transaction_id": existing.id,
                "idempotency_key": idempotency_key,
                "duplicate_count": existing.duplicate_count,
            },
            transaction_id=existing.id,
            actor=agent_id,
        )
        db.commit()
        db.refresh(existing)
        return existing

    started = time.perf_counter()
    snapshot = db.get(CheckoutSnapshot, checkout_id)
    if snapshot is None:
        raise ValueError("Checkout snapshot not found")
    if snapshot.merchant_id != merchant.id:
        raise ValueError("Checkout snapshot does not belong to this merchant")

    checks: list[Check] = []
    policy = current_policy(db, merchant.id)
    agent = db.scalar(
        select(Agent).where(Agent.merchant_id == merchant.id, Agent.agent_id == agent_id)
    )

    # The exact agent-signed body. Importantly, this uses the hash supplied by
    # the agent, while checkout-integrity later compares that signed value with
    # the merchant-authoritative stored snapshot hash.
    body = {
        "agent_id": agent_id,
        "mandate_id": mandate.id,
        "sku": sku,
        "quantity": quantity,
        "checkout_id": checkout_id,
        "checkout_hash": signed_checkout_hash,
        "nonce": nonce,
        "timestamp": timestamp,
    }
    canonical_body = canonical_json(body)

    if agent is None:
        action = policy.unknown_agent_action.upper()
        checks.append(
            Check(
                "Agent Identity",
                "STEP_UP" if action == "STEP_UP" else "FAIL",
                "UNKNOWN_AGENT",
                "Agent is not registered",
            )
        )
    elif agent.status != "ACTIVE" or agent.trust == "SUSPENDED":
        checks.append(Check("Agent Identity", "FAIL", "AGENT_SUSPENDED", "Agent is not active"))
    elif not verify_text(agent.public_key, canonical_body, signature):
        checks.append(
            Check(
                "Agent Identity",
                "FAIL",
                "AGENT_SIGNATURE_INVALID",
                "Ed25519 request signature failed",
            )
        )
    else:
        checks.append(Check("Agent Identity", "PASS", None, "Ed25519 request signature verified"))
        agent.last_seen_at = datetime.now(UTC)

    age = abs(int(time.time()) - timestamp)
    checks.append(
        Check(
            "Request Freshness",
            "PASS" if age <= 300 else "FAIL",
            None if age <= 300 else "STALE_AGENT_REQUEST",
            f"Request age {age}s",
        )
    )

    nonce_seen = db.scalar(
        select(AgentNonce).where(
            AgentNonce.merchant_id == merchant.id,
            AgentNonce.agent_id == agent_id,
            AgentNonce.nonce == nonce,
        )
    )
    checks.append(
        Check(
            "Replay",
            "FAIL" if nonce_seen else "PASS",
            "REPLAY_DETECTED" if nonce_seen else None,
            "Agent nonce already used" if nonce_seen else "Fresh agent nonce",
        )
    )

    mandate_signature_ok = verify_text(mandate.public_key, mandate.canonical_payload, mandate.signature)
    checks.append(
        Check(
            "Human Mandate",
            "PASS" if mandate_signature_ok else "FAIL",
            None if mandate_signature_ok else "MANDATE_SIGNATURE_INVALID",
            "Signed human authority verified" if mandate_signature_ok else "Mandate signature failed",
        )
    )

    mandate_binding_ok = (
        mandate.intent_id == intent.id
        and mandate.merchant_id == merchant.id
        and mandate.agent_id == agent_id
    )
    checks.append(
        Check(
            "Mandate Binding",
            "PASS" if mandate_binding_ok else "FAIL",
            None if mandate_binding_ok else "MANDATE_BINDING_MISMATCH",
            f"intent={intent.id}; agent={agent_id}; merchant={merchant.id}",
        )
    )

    expired = _aware(mandate.expires_at) <= datetime.now(UTC)
    checks.append(
        Check(
            "Mandate Expiry",
            "FAIL" if expired else "PASS",
            "MANDATE_EXPIRED" if expired else None,
            "Authorization expired" if expired else "Authorization active",
        )
    )

    consumed_invalid = mandate.status == "CONSUMED" and recovery_of_transaction_id is None
    checks.append(
        Check(
            "Mandate State",
            "FAIL" if consumed_invalid else "PASS",
            "MANDATE_ALREADY_CONSUMED" if consumed_invalid else None,
            mandate.status,
        )
    )

    requested_merchant = merchant_override or merchant.id
    merchant_ok = requested_merchant == merchant.id == mandate.merchant_id == intent.merchant_id
    checks.append(
        Check(
            "Merchant",
            "PASS" if merchant_ok else "FAIL",
            None if merchant_ok else "PAYEE_NOT_AUTHORIZED",
            requested_merchant,
        )
    )

    checkout_request_ok = snapshot.sku == sku and snapshot.quantity == quantity
    checks.append(
        Check(
            "Checkout Request Binding",
            "PASS" if checkout_request_ok else "FAIL",
            None if checkout_request_ok else "CHECKOUT_REQUEST_MISMATCH",
            f"snapshot={snapshot.sku} x{snapshot.quantity}; requested={sku} x{quantity}",
        )
    )

    brand_ok = not intent.brand or snapshot.brand.casefold() == intent.brand.casefold()
    category_ok = not intent.category or snapshot.category.casefold() == intent.category.casefold()
    checks.append(
        Check(
            "Brand",
            "PASS" if brand_ok else "FAIL",
            None if brand_ok else "MANDATE_BRAND_MISMATCH",
            snapshot.brand,
        )
    )
    checks.append(
        Check(
            "Category",
            "PASS" if category_ok else "FAIL",
            None if category_ok else "MANDATE_CATEGORY_MISMATCH",
            snapshot.category,
        )
    )
    allowed_variants = [str(v).casefold() for v in json.loads(intent.allowed_variants_json or "[]")]
    variant_ok = not allowed_variants or snapshot.variant.casefold() in allowed_variants
    checks.append(
        Check(
            "Variant",
            "PASS" if variant_ok else "FAIL",
            None if variant_ok else "MANDATE_VARIANT_MISMATCH",
            snapshot.variant,
        )
    )

    quantity_ok = snapshot.quantity <= intent.max_quantity
    product_row = db.scalar(
        select(Product).where(Product.merchant_id == merchant.id, Product.sku == snapshot.sku)
    )
    inventory_ok = product_row is not None and snapshot.quantity <= product_row.inventory
    amount_ok = snapshot.total_minor <= intent.max_amount_minor
    checks.append(
        Check(
            "Quantity",
            "PASS" if quantity_ok else "FAIL",
            None if quantity_ok else "MANDATE_QUANTITY_LIMIT",
            f"{snapshot.quantity} <= {intent.max_quantity}",
        )
    )
    checks.append(
        Check(
            "Inventory",
            "PASS" if inventory_ok else "FAIL",
            None if inventory_ok else "INVENTORY_EXCEEDED",
            f"requested {snapshot.quantity}; available {product_row.inventory if product_row else 0}",
        )
    )
    checks.append(
        Check(
            "Amount",
            "PASS" if amount_ok else "FAIL",
            None if amount_ok else "MANDATE_AMOUNT_LIMIT",
            f"{snapshot.total_minor} <= {intent.max_amount_minor}",
        )
    )

    catalog_assertion_ok = asserted_total_minor is None or asserted_total_minor == snapshot.total_minor
    checks.append(
        Check(
            "Price Authority",
            "PASS" if catalog_assertion_ok else "FAIL",
            None if catalog_assertion_ok else "AI_PRICE_MISMATCH",
            "Merchant catalog is authoritative",
        )
    )

    checkout_ok = signed_checkout_hash == snapshot.checkout_hash
    checks.append(
        Check(
            "Checkout Integrity",
            "PASS" if checkout_ok else "FAIL",
            None if checkout_ok else "CHECKOUT_MUTATED",
            f"signed={signed_checkout_hash}; authoritative={snapshot.checkout_hash}",
        )
    )

    merchant_limit_ok = snapshot.total_minor <= policy.max_transaction_minor
    checks.append(
        Check(
            "Merchant Limit",
            "PASS" if merchant_limit_ok else "FAIL",
            None if merchant_limit_ok else "MERCHANT_TRANSACTION_LIMIT",
            f"{snapshot.total_minor} <= {policy.max_transaction_minor}",
        )
    )

    step_up = snapshot.total_minor > policy.step_up_above_minor
    checks.append(
        Check(
            "Step-Up Threshold",
            "STEP_UP" if step_up else "PASS",
            "MERCHANT_STEP_UP_REQUIRED" if step_up else None,
            f"threshold {policy.step_up_above_minor}",
        )
    )

    # Count only today's already-allowed economic actions for the daily cap.
    now = datetime.now(UTC)
    start_of_day = datetime(now.year, now.month, now.day, tzinfo=UTC)
    allowed_today = db.scalar(
        select(func.coalesce(func.sum(Transaction.amount_minor), 0)).where(
            Transaction.merchant_id == merchant.id,
            Transaction.decision == "ALLOW",
            Transaction.created_at >= start_of_day,
        )
    ) or 0
    daily_ok = allowed_today + snapshot.total_minor <= policy.daily_spend_minor
    checks.append(
        Check(
            "Daily Spend",
            "PASS" if daily_ok else "FAIL",
            None if daily_ok else "MERCHANT_DAILY_SPEND_LIMIT",
            f"{allowed_today + snapshot.total_minor} <= {policy.daily_spend_minor}",
        )
    )

    if recovery_of_transaction_id:
        original = db.get(Transaction, recovery_of_transaction_id)
        recovery_ok = (
            original is not None
            and original.merchant_id == merchant.id
            and original.payment_state == "FAILED"
            and original.intent_id == intent.id
            and original.mandate_id == mandate.id
        )
        checks.append(
            Check(
                "Recovery Lineage",
                "PASS" if recovery_ok else "FAIL",
                None if recovery_ok else "RECOVERY_LINEAGE_INVALID",
                recovery_of_transaction_id,
            )
        )

    has_fail = any(check.result == "FAIL" for check in checks)
    has_step = any(check.result == "STEP_UP" for check in checks)
    decision = "BLOCKED" if has_fail else ("STEP-UP" if has_step else "ALLOW")
    reasons = [check.reason_code for check in checks if check.reason_code]
    economic_action_id = sha256_text(
        f"{mandate.id}|{snapshot.checkout_hash}|{recovery_of_transaction_id or 'root'}"
    )

    tx = Transaction(
        id=f"TX-{uuid.uuid4().hex[:8].upper()}",
        merchant_id=merchant.id,
        intent_id=intent.id,
        mandate_id=mandate.id,
        agent_id=agent_id,
        checkout_id=snapshot.id,
        economic_action_id=economic_action_id,
        idempotency_key=idempotency_key,
        amount_minor=snapshot.total_minor,
        currency=snapshot.currency,
        decision=decision,
        payment_state="NOT_SENT",
        reason_codes_json=json.dumps(reasons),
        latency_ms=max(1, int((time.perf_counter() - started) * 1000)),
        razorpay_api_calls=0,
        recovery_of_transaction_id=recovery_of_transaction_id,
    )
    db.add(tx)
    db.flush()

    for index, check in enumerate(checks, start=1):
        db.add(
            PolicyDecision(
                transaction_id=tx.id,
                check_name=check.name,
                result=check.result,
                reason_code=check.reason_code,
                detail=check.detail,
                sequence=index,
            )
        )

    # A valid registered-agent request consumes its transport nonce regardless
    # of the business decision; blocked requests must not be safely replayable.
    if nonce_seen is None and agent is not None:
        db.add(AgentNonce(merchant_id=merchant.id, agent_id=agent_id, nonce=nonce))

    append_audit(
        db,
        merchant.id,
        "INTENTLOCK_DECISION",
        {
            "transaction_id": tx.id,
            "decision": decision,
            "reason_codes": reasons,
            "checkout_id": snapshot.id,
            "checkout_hash": snapshot.checkout_hash,
            "signed_checkout_hash": signed_checkout_hash,
            "amount_minor": snapshot.total_minor,
            "razorpay_api_calls": 0,
        },
        transaction_id=tx.id,
        actor="intentlock-kernel",
    )

    if decision == "ALLOW" and create_payment:
        if recovery_of_transaction_id is None:
            mandate.status = "CONSUMED"
            mandate.consumed_at = datetime.now(UTC)
        create_order(db, tx)
    elif decision == "BLOCKED" and agent is not None:
        agent.violations += 1

    db.commit()
    db.refresh(tx)
    return tx


def transaction_checks(db: Session, transaction_id: str) -> list[PolicyDecision]:
    return list(
        db.scalars(
            select(PolicyDecision)
            .where(PolicyDecision.transaction_id == transaction_id)
            .order_by(PolicyDecision.sequence)
        ).all()
    )
