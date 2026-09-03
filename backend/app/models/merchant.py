from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Merchant(Base):
    __tablename__ = "merchants"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id"), unique=True, nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    environment: Mapped[str] = mapped_column(String(64), default="Razorpay Test Mode")
    status: Mapped[str] = mapped_column(String(32), default="ONBOARDING")
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    payment_test_connected: Mapped[bool] = mapped_column(Boolean, default=False)
    discovery_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    identity_active: Mapped[bool] = mapped_column(Boolean, default=False)
    identity_algorithm: Mapped[str | None] = mapped_column(String(32), nullable=True)
    identity_public_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    identity_fingerprint: Mapped[str | None] = mapped_column(String(96), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    owner = relationship("User", back_populates="merchant")
    products = relationship("Product", back_populates="merchant", cascade="all, delete-orphan")
    policies = relationship("MerchantPolicy", back_populates="merchant", cascade="all, delete-orphan")
