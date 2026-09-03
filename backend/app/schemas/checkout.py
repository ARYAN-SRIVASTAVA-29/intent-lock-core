from pydantic import BaseModel, Field


class CheckoutProposalRequest(BaseModel):
    sku: str = Field(min_length=1, max_length=80)
    quantity: int = Field(ge=1, le=25)


class CheckoutProposalResponse(BaseModel):
    checkout_id: str
    merchant_id: str
    merchant_name: str
    sku: str
    product: str
    brand: str
    category: str
    variant: str
    quantity: int
    unit_price_minor: int
    total_minor: int
    currency: str
    inventory_available: int
    price_authority: str
    checkout_hash: str
    status: str
