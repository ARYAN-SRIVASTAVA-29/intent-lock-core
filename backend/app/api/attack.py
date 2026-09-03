import json
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.transactions import serialize_tx
from app.core.dependencies import get_onboarded_merchant
from app.db.session import get_db
from app.models import Intent, Mandate, Merchant, Product, Transaction
from app.schemas.transactions import AttackRequest
from app.services.intents import authorize_mandate, compile_intent
from app.services.intentlock import build_reference_envelope, create_checkout_snapshot, evaluate_transaction
from app.services.payments import apply_payment_event

router = APIRouter(tags=["attack-lab"])

PRESETS = [
    {"name": "Prompt Injection", "description": "Compromised agent escalates the authorized quantity.", "quantity": 5},
    {"name": "Quantity Escalation", "description": "Agent requests more units than the human authorized.", "quantity": 5},
    {"name": "Wrong Product", "description": "Agent swaps the authorized product for another catalog item."},
    {"name": "Checkout Mutation", "description": "A valid agent signs a checkout hash and total that do not match merchant truth.", "tamper_checkout": True},
    {"name": "Forged Agent Signature", "description": "The economic request carries an invalid Ed25519 signature.", "forged_signature": True},
    {"name": "Wrong Merchant", "description": "The request attempts to redirect payment to an unauthorized merchant."},
    {"name": "Replay Mandate", "description": "The same signed transport nonce is submitted again."},
    {"name": "Duplicate Invocation", "description": "The same economic action is delivered three times."},
    {"name": "Expired Authorization", "description": "The request arrives after the mandate has expired.", "expire_authorization": True},
    {"name": "Unauthorized Recovery", "description": "Recovery attempts to exceed the original quantity authority."},
    {"name": "Custom Payload", "description": "Edit the agent payload and run it through the production evaluator."},
]


def _products(db: Session, merchant_id: str):
    return list(db.scalars(select(Product).where(Product.merchant_id == merchant_id, Product.visible.is_(True)).order_by(Product.price_minor.asc())).all())


def _setup(db: Session, merchant: Merchant, *, expired: bool = False):
    products = _products(db, merchant.id)
    if not products:
        raise HTTPException(409, "Upload a visible catalog before using Attack Lab")
    base = products[0]
    intent = compile_intent(db, merchant, f"Buy one {base.brand} {base.category} under ₹{base.price_minor//100:,}", sku=base.sku, max_amount_minor=base.price_minor, max_quantity=1)
    mandate = authorize_mandate(db, merchant, intent, force_expired=expired)
    return products, base, intent, mandate


@router.get("/attack-lab/config")
def attack_config(merchant: Merchant = Depends(get_onboarded_merchant), db: Session = Depends(get_db)):
    products = _products(db, merchant.id)
    if not products:
        raise HTTPException(409, "Upload a visible catalog before using Attack Lab")
    base = products[0]
    return {
        "merchant_id": merchant.id,
        "authority": {
            "sku": base.sku,
            "product": base.product,
            "brand": base.brand,
            "category": base.category,
            "max_quantity": 1,
            "max_amount_minor": base.price_minor,
            "currency": base.currency,
        },
        "products": [
            {
                "sku": p.sku,
                "product": p.product,
                "brand": p.brand,
                "category": p.category,
                "unit_price_minor": p.price_minor,
                "currency": p.currency,
                "inventory": p.inventory,
            }
            for p in products
        ],
        "presets": PRESETS,
    }


def _run(db, merchant, intent, mandate, product, quantity, *, idempotency=None, nonce=None, checkout_hash_override=None, asserted_total_minor=None, merchant_override=None, recovery_of=None, forged_signature=False):
    snapshot = create_checkout_snapshot(db, merchant, product.sku, quantity)
    envelope = build_reference_envelope(
        db, merchant, mandate, snapshot, nonce=nonce, checkout_hash_override=checkout_hash_override
    )
    return evaluate_transaction(
        db, merchant, intent=intent, mandate=mandate, sku=product.sku, quantity=quantity,
        checkout_id=snapshot.id, signed_checkout_hash=envelope["checkout_hash"],
        agent_id=envelope["agent_id"], nonce=envelope["nonce"], timestamp=envelope["timestamp"],
        signature=("forged-signature" if forged_signature else envelope["signature"]),
        idempotency_key=idempotency or f"atk_{uuid.uuid4().hex}",
        asserted_total_minor=asserted_total_minor, merchant_override=merchant_override,
        recovery_of_transaction_id=recovery_of,
    )


@router.post("/attack-lab/run")
def run_attack(payload: AttackRequest, merchant: Merchant = Depends(get_onboarded_merchant), db: Session = Depends(get_db)):
    scenario = payload.scenario.strip().lower().replace("_", " ")
    expired = payload.expire_authorization if payload.expire_authorization is not None else scenario in {"expired authorization", "expired mandate"}
    products, base, intent, mandate = _setup(db, merchant, expired=expired)
    requested = base
    quantity = payload.quantity or 1
    kwargs = {}

    if payload.sku:
        requested = next((p for p in products if p.sku == payload.sku), None)
        if requested is None:
            raise HTTPException(400, "Selected attack SKU is not a visible merchant product")

    if scenario in {"prompt injection", "quantity escalation"} and payload.quantity is None:
        quantity = 5
    elif scenario in {"wrong product", "unauthorized product"}:
        if payload.sku is None:
            requested = next((p for p in products if p.brand.casefold() != base.brand.casefold()), products[-1])
    elif scenario == "wrong merchant":
        kwargs["merchant_override"] = payload.merchant_override or "merchant_untrusted_77"
    elif scenario == "checkout mutation":
        if payload.tamper_checkout is not False:
            kwargs["checkout_hash_override"] = "0" * 64
        kwargs["asserted_total_minor"] = payload.asserted_total_minor or (requested.price_minor * quantity + 250_000)
    elif scenario in {"forged agent signature", "forged signature"}:
        kwargs["forged_signature"] = payload.forged_signature is not False
    elif scenario in {"expired authorization", "expired mandate"}:
        pass
    elif scenario == "replay mandate":
        nonce = f"replay_{uuid.uuid4().hex}"
        first = _run(db, merchant, intent, mandate, base, 1, nonce=nonce)
        second = _run(db, merchant, intent, mandate, base, 1, nonce=nonce)
        body = serialize_tx(db, second).model_dump(mode="json")
        return {"scenario": payload.scenario, "result": second.decision, "transaction": body, "razorpay_api_calls": second.razorpay_api_calls, "first_transaction_id": first.id}
    elif scenario == "duplicate invocation":
        key = f"dup_{uuid.uuid4().hex}"
        snapshot = create_checkout_snapshot(db, merchant, base.sku, 1)
        env = build_reference_envelope(db, merchant, mandate, snapshot)
        common = dict(
            intent=intent, mandate=mandate, sku=base.sku, quantity=1, checkout_id=snapshot.id,
            signed_checkout_hash=env["checkout_hash"], agent_id=env["agent_id"], nonce=env["nonce"],
            timestamp=env["timestamp"], signature=env["signature"], idempotency_key=key,
        )
        first = evaluate_transaction(db, merchant, **common)
        evaluate_transaction(db, merchant, **common)
        third = evaluate_transaction(db, merchant, **common)
        return {"scenario": payload.scenario, "result": "CONTAINED", "transaction": serialize_tx(db, third).model_dump(mode="json"), "tool_requests": 3, "economic_actions": 1, "duplicates_prevented": third.duplicate_count, "payment_orders": 1, "razorpay_orders": 1 if third.razorpay_api_calls else 0}
    elif scenario == "unauthorized recovery":
        first = _run(db, merchant, intent, mandate, base, 1)
        if first.decision == "ALLOW":
            apply_payment_event(db, first, "FAILED", verified=False); db.commit()
        # Deliberately exceed the original quantity while preserving recovery lineage.
        recovery = _run(db, merchant, intent, mandate, base, 2, recovery_of=first.id)
        return {"scenario": payload.scenario, "result": recovery.decision, "transaction": serialize_tx(db, recovery).model_dump(mode="json"), "razorpay_api_calls": recovery.razorpay_api_calls, "original_transaction_id": first.id}
    elif scenario not in {"valid purchase", "happy path", "custom payload"}:
        raise HTTPException(400, "Unknown Attack Lab scenario")

    if payload.merchant_override and "merchant_override" not in kwargs:
        kwargs["merchant_override"] = payload.merchant_override
    if payload.asserted_total_minor and "asserted_total_minor" not in kwargs:
        kwargs["asserted_total_minor"] = payload.asserted_total_minor
    if payload.tamper_checkout and "checkout_hash_override" not in kwargs:
        kwargs["checkout_hash_override"] = "0" * 64
    if payload.forged_signature and "forged_signature" not in kwargs:
        kwargs["forged_signature"] = True

    tx = _run(db, merchant, intent, mandate, requested, quantity, **kwargs)
    return {
        "scenario": payload.scenario,
        "result": tx.decision,
        "transaction": serialize_tx(db, tx).model_dump(mode="json"),
        "razorpay_api_calls": tx.razorpay_api_calls,
        "authority": {"sku": base.sku, "product": base.product, "max_quantity": 1, "max_amount_minor": base.price_minor, "merchant_id": merchant.id},
        "submitted_payload": {"sku": requested.sku, "product": requested.product, "quantity": quantity, "asserted_total_minor": kwargs.get("asserted_total_minor", requested.price_minor * quantity), "merchant_id": kwargs.get("merchant_override", merchant.id), "checkout_tampered": bool(kwargs.get("checkout_hash_override")), "signature_forged": bool(kwargs.get("forged_signature")), "authorization_expired": expired},
    }
