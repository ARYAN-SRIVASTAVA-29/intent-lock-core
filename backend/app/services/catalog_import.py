import csv, io, json
from typing import Any
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models import Product

REQUIRED = {"sku", "brand", "category", "inventory"}

def _bool(v: Any) -> bool:
    if isinstance(v,bool): return v
    return str(v).strip().lower() not in {"false","0","no","hidden"}

def _normalize(row: dict[str, Any]) -> dict[str, Any]:
    missing = [k for k in REQUIRED if row.get(k) in (None,"")]
    product = row.get("product") or row.get("name")
    if not product: missing.append("product/name")
    if missing: raise HTTPException(422, f"Missing required catalog fields: {', '.join(missing)}")
    if row.get("price_minor") not in (None,""):
        price_minor=int(row["price_minor"])
    elif row.get("price") not in (None,""):
        price_minor=round(float(str(row["price"]).replace(",","").replace("₹",""))*100)
    else: raise HTTPException(422,"Catalog row must include price or price_minor")
    inv=int(row["inventory"])
    if price_minor < 0 or inv < 0: raise HTTPException(422,"Price and inventory cannot be negative")
    return dict(sku=str(row["sku"]).strip(), product=str(product).strip(), brand=str(row["brand"]).strip(), category=str(row["category"]).strip(), price_minor=price_minor, currency=str(row.get("currency") or "INR").upper(), inventory=inv, variant=str(row.get("variant") or "Default"), delivery_days=int(row.get("delivery_days") or 3), visible=_bool(row.get("visible",True)))

def parse_catalog(filename: str, raw: bytes) -> list[dict[str, Any]]:
    name=filename.lower()
    try:
        if name.endswith('.csv'):
            rows=list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))))
        elif name.endswith('.json'):
            data=json.loads(raw.decode('utf-8'))
            rows=data.get('items', data) if isinstance(data,dict) else data
            if not isinstance(rows,list): raise ValueError('JSON must be an array or {items: [...]}')
        else: raise HTTPException(415,'Upload a .csv or .json catalog')
    except HTTPException: raise
    except Exception as e: raise HTTPException(422,f'Invalid catalog file: {e}') from e
    items=[_normalize(dict(r)) for r in rows]
    if not items: raise HTTPException(422,'Catalog file is empty')
    skus=[i['sku'] for i in items]
    if len(skus)!=len(set(skus)): raise HTTPException(422,'Duplicate SKU found in uploaded catalog')
    return items

def replace_catalog(db: Session, merchant_id: str, items: list[dict[str, Any]]) -> None:
    db.query(Product).filter(Product.merchant_id==merchant_id).delete(synchronize_session=False)
    for item in items: db.add(Product(merchant_id=merchant_id, **item))
    db.commit()
