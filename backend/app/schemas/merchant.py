from pydantic import BaseModel

from app.schemas.catalog import CatalogSummary


class MerchantResponse(BaseModel):
    merchant_id: str
    merchant_name: str
    environment: str
    status: str
    onboarding_completed: bool
    payment_test_connected: bool
    discovery_enabled: bool
    identity_active: bool
    identity_algorithm: str | None
    identity_fingerprint: str | None
    policy_version: str
    policy_status: str
    catalog: CatalogSummary
