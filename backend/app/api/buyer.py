import re
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.dependencies import get_onboarded_merchant
from app.db.session import get_db
from app.models import Merchant,Product

router=APIRouter(tags=['reference-buyer'])

class BuyerPlanRequest(BaseModel):
    request:str=Field(min_length=3,max_length=1000)

class BuyerMatch(BaseModel):
    sku:str
    product:str
    brand:str
    category:str
    variant:str
    quantity:int
    unit_price_minor:int
    total_minor:int
    currency:str
    inventory:int
    delivery_days:int
    fit_score:int
    recommendation_label:str

class BuyerPlanResponse(BaseModel):
    agent_id:str
    planning_mode:str
    request:str
    sku:str
    product:str
    brand:str
    category:str
    variant:str
    quantity:int
    unit_price_minor:int
    max_amount_minor:int
    currency:str
    tool_trace:list[str]
    explanation:str
    matches:list[BuyerMatch]
    recommended_sku:str
    recommendation_reason:str

def _parse_budget(text:str)->int|None:
    for pattern in [r'₹\s*([\d,]+)',r'(?:under|below|max(?:imum)?|budget(?: of)?)\s+(?:rs\.?|inr|₹)?\s*([\d,]+)']:
        m=re.search(pattern,text,re.I)
        if m:return int(m.group(1).replace(',',''))*100
    return None

def _parse_qty(text:str)->int:
    low=text.lower(); words={'one':1,'two':2,'three':3,'four':4,'five':5}
    for w,n in words.items():
        if re.search(rf'\b{w}\b',low):return n
    m=re.search(r'\b(?:qty|quantity)\s*[:=]?\s*(\d+)\b',low)
    return int(m.group(1)) if m else 1

@router.post('/buyer-agent/plan',response_model=BuyerPlanResponse)
def plan(payload:BuyerPlanRequest,merchant:Merchant=Depends(get_onboarded_merchant),db:Session=Depends(get_db)):
    items=list(db.scalars(select(Product).where(Product.merchant_id==merchant.id,Product.visible.is_(True),Product.inventory>0)).all())
    if not items:raise HTTPException(409,'No visible in-stock products are available to the buyer agent')
    text=payload.request.lower();budget=_parse_budget(payload.request);qty=_parse_qty(payload.request)
    brands={p.brand.lower():p.brand for p in items};categories={p.category.lower():p.category for p in items}
    requested_brand=next((canonical for key,canonical in brands.items() if key in text),None)
    requested_category=next((canonical for key,canonical in categories.items() if key in text),None)
    if requested_category is None:
        category_hints=[('phone',['smartphone','phone']),('mobile',['smartphone','phone']),('tablet',['tablet']),('earbud',['earbud']),('buds',['earbud']),('headphone',['headphone'])]
        hint=next((targets for word,targets in category_hints if word in text),None)
        if hint:
            requested_category=next((p.category for p in items if any(target in p.category.lower() for target in hint)),None)
    color_words=['black','blue','white','silver','green','red','violet','gray','grey','gold']
    requested_colors=[c for c in color_words if c in text]
    eligible=[p for p in items if p.inventory>=qty and (budget is None or p.price_minor*qty<=budget) and (requested_brand is None or p.brand==requested_brand) and (requested_category is None or p.category==requested_category)]
    if not eligible:raise HTTPException(409,'No in-stock catalog item satisfies the requested quantity and budget')
    def score_points(p:Product):
        points=0
        if requested_brand and p.brand==requested_brand:points+=20
        if requested_category and p.category==requested_category:points+=12
        if p.product.lower() in text:points+=30
        if any(c in p.variant.lower() for c in requested_colors):points+=5
        for token in re.findall(r'[a-z0-9]+',text):
            if len(token)>3 and token in f'{p.product} {p.brand} {p.category} {p.variant}'.lower():points+=1
        return points
    eligible.sort(key=lambda p:(-score_points(p),p.price_minor));chosen=eligible[0]
    max_amount=budget or chosen.price_minor*qty
    top=eligible[:12]
    raw_scores=[score_points(p) for p in top]
    score_ceiling=max(1,max(raw_scores,default=1))
    matches=[]
    for index,p in enumerate(top):
        semantic=score_points(p)
        budget_fit=0 if budget is None else max(0,round((1-(p.price_minor*qty/budget))*18))
        fit=min(99,70+round((semantic/score_ceiling)*20)+budget_fit)
        label='Recommended' if index==0 else ('Best value' if p.price_minor==min(x.price_minor for x in top) else 'Strong match')
        matches.append(BuyerMatch(sku=p.sku,product=p.product,brand=p.brand,category=p.category,variant=p.variant,quantity=qty,unit_price_minor=p.price_minor,total_minor=p.price_minor*qty,currency=p.currency,inventory=p.inventory,delivery_days=p.delivery_days,fit_score=fit,recommendation_label=label))
    reason=(f'{chosen.product} is the strongest match across the requested category, budget, availability and catalog attributes. '
            'The recommendation is advisory; the buyer chooses the exact SKU before authorization.')
    return BuyerPlanResponse(agent_id='buyer-agent-17',planning_mode='DETERMINISTIC_MULTI_MATCH',request=payload.request,sku=chosen.sku,product=chosen.product,brand=chosen.brand,category=chosen.category,variant=chosen.variant,quantity=qty,unit_price_minor=chosen.price_minor,max_amount_minor=max_amount,currency=chosen.currency,tool_trace=['discover_merchant()','search_catalog()','rank_eligible_products()','compare_price_inventory_delivery()','recommend_product()'],explanation=f'Found {len(eligible)} eligible catalog matches. Merchant catalog remains authoritative for price.',matches=matches,recommended_sku=chosen.sku,recommendation_reason=reason)
