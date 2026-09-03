from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Product
from app.schemas.catalog import CatalogSummary
from app.services.seed import MERCHANT_ID


def catalog_summary(db: Session, merchant_id: str = MERCHANT_ID) -> CatalogSummary:
    products = db.scalar(
        select(func.count(func.distinct(Product.product))).where(Product.merchant_id == merchant_id)
    ) or 0
    skus = db.scalar(select(func.count(Product.id)).where(Product.merchant_id == merchant_id)) or 0
    brands = db.scalar(
        select(func.count(func.distinct(Product.brand))).where(Product.merchant_id == merchant_id)
    ) or 0
    categories = db.scalar(
        select(func.count(func.distinct(Product.category))).where(Product.merchant_id == merchant_id)
    ) or 0
    visible_skus = db.scalar(
        select(func.count(Product.id)).where(
            Product.merchant_id == merchant_id, Product.visible.is_(True)
        )
    ) or 0
    last_updated_at = db.scalar(
        select(func.max(Product.updated_at)).where(Product.merchant_id == merchant_id)
    )
    return CatalogSummary(
        merchant_id=merchant_id,
        products=products,
        skus=skus,
        brands=brands,
        categories=categories,
        visible_skus=visible_skus,
        last_updated_at=last_updated_at,
    )
