from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class MerchantPolicy(Base):
    __tablename__ = "merchant_policies"
    __table_args__ = (UniqueConstraint("merchant_id", "version", name="uq_policy_merchant_version"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    merchant_id: Mapped[str] = mapped_column(ForeignKey("merchants.id"), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(32), nullable=False, default="v1")
    status: Mapped[str] = mapped_column(String(32), default="PUBLISHED")
    max_transaction_minor: Mapped[int] = mapped_column(Integer, default=5_000_000)
    step_up_above_minor: Mapped[int] = mapped_column(Integer, default=2_500_000)
    daily_spend_minor: Mapped[int] = mapped_column(Integer, default=10_000_000)
    max_discount_pct: Mapped[float] = mapped_column(Numeric(5, 2), default=5.0)
    max_recovery_attempts: Mapped[int] = mapped_column(Integer, default=2)
    alternative_skus_allowed: Mapped[bool] = mapped_column(Boolean, default=True)
    merchant_switching_allowed: Mapped[bool] = mapped_column(Boolean, default=False)
    unknown_agent_action: Mapped[str] = mapped_column(String(32), default="STEP_UP")
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    merchant = relationship("Merchant", back_populates="policies")
