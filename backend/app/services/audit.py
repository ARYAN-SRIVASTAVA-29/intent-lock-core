import json
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AuditEvent
from app.services.crypto import canonical_json, sha256_text


def append_audit(
    db: Session,
    merchant_id: str,
    event_type: str,
    payload: dict[str, Any],
    *,
    transaction_id: str | None = None,
    actor: str = "system",
) -> AuditEvent:
    latest = db.scalar(
        select(AuditEvent)
        .where(AuditEvent.merchant_id == merchant_id)
        .order_by(AuditEvent.sequence.desc())
        .limit(1)
    )
    sequence = (latest.sequence if latest else 0) + 1
    previous_hash = latest.event_hash if latest else ""
    payload_json = canonical_json(payload)
    event_hash = sha256_text(f"{sequence}|{payload_json}|{previous_hash}")
    event = AuditEvent(
        merchant_id=merchant_id,
        transaction_id=transaction_id,
        sequence=sequence,
        event_type=event_type,
        actor=actor,
        payload_json=payload_json,
        previous_hash=previous_hash,
        event_hash=event_hash,
    )
    db.add(event)
    db.flush()
    return event


def verify_chain(db: Session, merchant_id: str) -> tuple[bool, int, int | None]:
    events = db.scalars(
        select(AuditEvent).where(AuditEvent.merchant_id == merchant_id).order_by(AuditEvent.sequence)
    ).all()
    previous = ""
    for event in events:
        expected = sha256_text(f"{event.sequence}|{event.payload_json}|{previous}")
        if event.previous_hash != previous or event.event_hash != expected:
            return False, len(events), event.sequence
        previous = event.event_hash
    return True, len(events), None


def audit_payload(event: AuditEvent) -> dict[str, Any]:
    try:
        payload = json.loads(event.payload_json)
    except Exception:
        payload = {}
    return {
        "sequence": event.sequence,
        "event_type": event.event_type,
        "actor": event.actor,
        "transaction_id": event.transaction_id,
        "payload": payload,
        "previous_hash": event.previous_hash,
        "event_hash": event.event_hash,
        "created_at": event.created_at,
    }
