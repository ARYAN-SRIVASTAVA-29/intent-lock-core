from pydantic import BaseModel


class ProtocolStatus(BaseModel):
    rest: str
    acp: str
    ucp: str
    mcp: str
    x402: str


class DiscoveryResponse(BaseModel):
    merchant_id: str
    merchant_name: str
    status: str
    environment: str
    catalog_endpoint: str
    policy_endpoint: str
    checkout_endpoint: str
    transaction_endpoint: str
    discovery_endpoint: str
    products: int
    skus: int
    brands: int
    categories: int
    policy_version: str
    protocols: ProtocolStatus


class DiscoveryTestStep(BaseModel):
    step: str
    status: str


class DiscoveryTestResponse(BaseModel):
    result: str
    merchant_id: str
    checks: list[DiscoveryTestStep]
