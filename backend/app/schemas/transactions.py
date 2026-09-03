from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class IntentCompileRequest(BaseModel):
    natural_language: str = Field(min_length=3, max_length=1000)
    sku: str | None = None
    max_amount_minor: int | None = Field(default=None, ge=1)
    max_quantity: int | None = Field(default=None, ge=1, le=25)


class IntentResponse(BaseModel):
    intent_id: str
    natural_language: str
    brand: str | None
    category: str | None
    max_amount_minor: int
    max_quantity: int
    allowed_variants: list[str]
    status: str


class MandateCreateRequest(BaseModel):
    intent_id: str
    agent_id: str = "buyer-agent-17"
    expires_minutes: int = Field(default=120, ge=1, le=1440)


class MandateResponse(BaseModel):
    mandate_id: str
    intent_id: str
    agent_id: str
    payload_hash: str
    signature: str
    status: str
    expires_at: datetime


class DemoExecuteRequest(BaseModel):
    sku: str | None = None
    quantity: int = Field(default=1, ge=1, le=25)
    max_quantity: int = Field(default=1, ge=1, le=25)
    max_amount_minor: int | None = Field(default=None, ge=1)
    natural_language: str | None = None
    payment_outcome: str | None = Field(default=None, pattern="^(CAPTURED|FAILED|AUTHORIZED)$")


class AgentTransactionRequest(BaseModel):
    intent_id: str
    mandate_id: str
    sku: str
    quantity: int = Field(ge=1, le=25)
    checkout_id: str
    checkout_hash: str
    agent_id: str
    nonce: str
    timestamp: int
    signature: str
    idempotency_key: str = Field(min_length=3, max_length=128)
    asserted_total_minor: int | None = None


class CheckResponse(BaseModel):
    name: str
    result: str
    reason_code: str | None
    detail: str


class TransactionResponse(BaseModel):
    transaction_id: str
    intent_id: str
    mandate_id: str
    agent_id: str
    checkout_id: str
    sku: str
    product: str
    quantity: int
    amount_minor: int
    currency: str
    decision: str
    payment_state: str
    reason_codes: list[str]
    latency_ms: int
    razorpay_api_calls: int
    duplicate_count: int
    recovery_of_transaction_id: str | None
    created_at: datetime
    intent_text: str = ""
    intent_brand: str | None = None
    intent_category: str | None = None
    intent_max_amount_minor: int = 0
    intent_max_quantity: int = 0
    mandate_status: str = ""
    mandate_payload_hash: str = ""
    mandate_expires_at: datetime | None = None
    checkout_hash: str = ""
    unit_price_minor: int = 0
    price_authority: str = "MERCHANT_CATALOG"
    payment_order_id: str | None = None
    payment_mode: str | None = None
    payment_id: str | None = None
    payment_signature_verified: bool | None = None
    inventory_after: int | None = None
    checks: list[CheckResponse] = []


class PaymentSimulationRequest(BaseModel):
    outcome: str = Field(pattern="^(CAPTURED|FAILED|AUTHORIZED)$")


class PaymentVerifyRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


class RecoveryRequest(BaseModel):
    sku: str
    quantity: int = Field(default=1, ge=1, le=25)


class AttackRequest(BaseModel):
    scenario: str
    sku: str | None = None
    quantity: int | None = Field(default=None, ge=1, le=25)
    asserted_total_minor: int | None = Field(default=None, ge=1)
    merchant_override: str | None = Field(default=None, max_length=128)
    tamper_checkout: bool | None = None
    forged_signature: bool | None = None
    expire_authorization: bool | None = None


class DashboardResponse(BaseModel):
    merchant: dict[str, Any]
    commerce: dict[str, Any]
    enforcement: dict[str, Any]
    transactions: list[dict[str, Any]]
    live_events: list[dict[str, Any]]
    agents: dict[str, Any]
    payments: dict[str, Any]
    audit: dict[str, Any]
