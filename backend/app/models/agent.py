from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Agent(Base):
    __tablename__ = "agents"
    __table_args__ = (UniqueConstraint("merchant_id", "agent_id", name="uq_agent_merchant_agent"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    merchant_id: Mapped[str] = mapped_column(ForeignKey("merchants.id"), nullable=False, index=True)
    agent_id: Mapped[str] = mapped_column(String(96), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(96), default="Reference Buyer")
    trust: Mapped[str] = mapped_column(String(32), default="VERIFIED")
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE")
    algorithm: Mapped[str] = mapped_column(String(32), default="Ed25519")
    public_key: Mapped[str] = mapped_column(Text, nullable=False)
    # Demo-only. Production keys belong in a KMS/HSM, never in this table.
    demo_private_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    violations: Mapped[int] = mapped_column(Integer, default=0)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
