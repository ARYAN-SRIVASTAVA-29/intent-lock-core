from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import or_, select
from sqlalchemy.orm import Session
from app.core.dependencies import get_current_merchant, get_onboarded_merchant
from app.db.session import get_db
from app.models import Merchant, Product
from app.schemas.catalog import CatalogResponse
from app.services.catalog import catalog_summary
from app.services.catalog_import import parse_catalog, replace_catalog
from app.services.seed import seed_products_for_merchant

router=APIRouter(tags=['catalog'])

def _query(mid:str, search:str|None, visible:bool):
    stmt=select(Product).where(Product.merchant_id==mid)
    if visible: stmt=stmt.where(Product.visible.is_(True))
    if search:
        t=f"%{search.strip()}%"; stmt=stmt.where(or_(Product.sku.ilike(t),Product.product.ilike(t),Product.brand.ilike(t),Product.category.ilike(t)))
    return stmt.order_by(Product.brand,Product.product,Product.variant)

def _response(db, mid, search=None, visible=False):
    return CatalogResponse(summary=catalog_summary(db,mid),items=list(db.scalars(_query(mid,search,visible)).all()))

@router.get('/catalog/products',response_model=CatalogResponse)
def private_catalog(search:str|None=Query(None), merchant:Merchant=Depends(get_onboarded_merchant), db:Session=Depends(get_db)): return _response(db,merchant.id,search,False)

@router.post('/catalog/demo',response_model=CatalogResponse)
def demo_catalog(merchant:Merchant=Depends(get_current_merchant),db:Session=Depends(get_db)):
    seed_products_for_merchant(db,merchant.id,replace=True); db.commit(); return _response(db,merchant.id)

@router.post('/catalog/upload',response_model=CatalogResponse)
async def upload_catalog(file:UploadFile=File(...), merchant:Merchant=Depends(get_current_merchant),db:Session=Depends(get_db)):
    items=parse_catalog(file.filename or 'catalog',await file.read()); replace_catalog(db,merchant.id,items); return _response(db,merchant.id)

@router.get('/agent-commerce/merchants/{merchant_id}/catalog',response_model=CatalogResponse)
def public_agent_catalog(merchant_id:str,search:str|None=Query(None),db:Session=Depends(get_db)):
    merchant=db.get(Merchant,merchant_id)
    if merchant is None: raise HTTPException(404,'Merchant not found')
    if not merchant.discovery_enabled: raise HTTPException(409,'Merchant agent discovery is not enabled')
    return _response(db,merchant_id,search,True)

@router.get('/agent-commerce/catalog',response_model=CatalogResponse)
def current_agent_catalog(search:str|None=Query(None),merchant:Merchant=Depends(get_current_merchant),db:Session=Depends(get_db)): return _response(db,merchant.id,search,True)
