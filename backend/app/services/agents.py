from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Agent
from app.services.crypto import generate_ed25519_keypair

REFERENCE_AGENT_ID = "buyer-agent-17"


def ensure_reference_agent(db: Session, merchant_id: str) -> Agent:
    agent = db.scalar(select(Agent).where(Agent.merchant_id == merchant_id, Agent.agent_id == REFERENCE_AGENT_ID))
    if agent is None:
        private_pem, public_pem = generate_ed25519_keypair()
        agent = Agent(
            merchant_id=merchant_id,
            agent_id=REFERENCE_AGENT_ID,
            provider="Reference Buyer",
            trust="VERIFIED",
            status="ACTIVE",
            public_key=public_pem,
            demo_private_key=private_pem,
            last_seen_at=datetime.now(UTC),
        )
        db.add(agent)
        db.flush()
    return agent
