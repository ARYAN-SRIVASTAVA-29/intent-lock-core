from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CatalogProduct(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sku: str
    product: str
    brand: str
    category: str
    price_minor: int
    currency: str
    inventory: int
    variant: str
    delivery_days: int
    visible: bool
    updated_at: datetime


class CatalogSummary(BaseModel):
    merchant_id: str
    products: int
    skus: int
    brands: int
    categories: int
    visible_skus: int
    last_updated_at: datetime | None = None


class CatalogResponse(BaseModel):
    summary: CatalogSummary
    items: list[CatalogProduct]
