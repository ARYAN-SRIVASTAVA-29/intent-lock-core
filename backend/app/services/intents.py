import json
import re
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Intent, Mandate, Merchant, Product
from app.services.agents import ensure_reference_agent
from app.services.audit import append_audit
from app.services.crypto import canonical_json, generate_ed25519_keypair, sha256_text, sign_text


def _money_limit(text: str, fallback: int) -> int:
    patterns = [r"₹\s*([\d,]+)", r"(?:under|max(?:imum)?|below)\s+(?:rs\.?|inr|₹)?\s*([\d,]+)"]
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return int(match.group(1).replace(",", "")) * 100
    return fallback


def _quantity(text: str) -> int:
    lower = text.lower()
    words = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5}
    for word, number in words.items():
        if re.search(rf"\b{word}\b", lower):
            return number
    m = re.search(r"\b(?:qty|quantity)\s*[:=]?\s*(\d+)\b", lower)
    return int(m.group(1)) if m else 1


def compile_intent(
    db: Session,
    merchant: Merchant,
    natural_language: str,
    *,
    sku: str | None = None,
    max_amount_minor: int | None = None,
    max_quantity: int | None = None,
) -> Intent:
    product = None
    if sku:
        product = db.scalar(select(Product).where(Product.merchant_id == merchant.id, Product.sku == sku))
    if product is None:
        items = db.scalars(select(Product).where(Product.merchant_id == merchant.id, Product.visible.is_(True))).all()
        lower = natural_language.lower()
        product = next((p for p in items if p.brand.lower() in lower or p.product.lower() in lower), None)
        product = product or (items[0] if items else None)
    if product is None:
        raise ValueError("Merchant catalog has no visible product to compile against")
    fallback = product.price_minor * max(1, max_quantity or _quantity(natural_language))
    intent = Intent(
        id=f"INT-{uuid.uuid4().hex[:8].upper()}",
        merchant_id=merchant.id,
        natural_language=natural_language,
        brand=product.brand,
        category=product.category,
        max_amount_minor=max_amount_minor or _money_limit(natural_language, fallback),
        max_quantity=max_quantity or _quantity(natural_language),
        allowed_variants_json=json.dumps([product.variant]),
        status="COMPILED",
    )
    db.add(intent)
    db.flush()
    append_audit(db, merchant.id, "INTENT_COMPILED", {
        "intent_id": intent.id,
        "brand": intent.brand,
        "category": intent.category,
        "max_amount_minor": intent.max_amount_minor,
        "max_quantity": intent.max_quantity,
    }, actor="human")
    return intent


def authorize_mandate(
    db: Session,
    merchant: Merchant,
    intent: Intent,
    *,
    agent_id: str = "buyer-agent-17",
    expires_minutes: int = 120,
    force_expired: bool = False,
) -> Mandate:
    ensure_reference_agent(db, merchant.id)
    expires_at = datetime.now(UTC) + timedelta(minutes=(-1 if force_expired else expires_minutes))
    payload = {
        "intent_id": intent.id,
        "merchant_id": merchant.id,
        "agent_id": agent_id,
        "brand": intent.brand,
        "category": intent.category,
        "max_amount_minor": intent.max_amount_minor,
        "max_quantity": intent.max_quantity,
        "allowed_variants": json.loads(intent.allowed_variants_json or "[]"),
        "currency": "INR",
        "expires_at": expires_at.isoformat(),
        "nonce": f"mn_{uuid.uuid4().hex}",
    }
    canonical = canonical_json(payload)
    private_pem, public_pem = generate_ed25519_keypair()
    mandate = Mandate(
        id=f"MAN-{uuid.uuid4().hex[:8].upper()}",
        merchant_id=merchant.id,
        intent_id=intent.id,
        agent_id=agent_id,
        canonical_payload=canonical,
        payload_hash=sha256_text(canonical),
        signature=sign_text(private_pem, canonical),
        public_key=public_pem,
        nonce=payload["nonce"],
        status="ACTIVE",
        expires_at=expires_at,
    )
    db.add(mandate)
    db.flush()
    append_audit(db, merchant.id, "MANDATE_AUTHORIZED", {
        "mandate_id": mandate.id,
        "intent_id": intent.id,
        "payload_hash": mandate.payload_hash,
        "expires_at": expires_at.isoformat(),
    }, actor="human")
    return mandate
