import json
import uuid
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.dependencies import get_onboarded_merchant
from app.db.session import get_db
from app.models import CheckoutSnapshot,Intent,Mandate,Merchant,Product,RazorpayOrder,RecoveryCase,Transaction
from app.schemas.transactions import RecoveryRequest,TransactionResponse
from app.api.transactions import serialize_tx
from app.services.intentlock import build_reference_envelope,create_checkout_snapshot,evaluate_transaction,current_policy
from app.services.payments import apply_payment_event

router=APIRouter(tags=['recovery'])

@router.get('/recovery')
def list_recovery(merchant:Merchant=Depends(get_onboarded_merchant),db:Session=Depends(get_db)):
    rows=db.scalars(select(RecoveryCase).where(RecoveryCase.merchant_id==merchant.id).order_by(RecoveryCase.created_at.desc())).all()
    items=[]
    for r in rows:
        tx=db.get(Transaction,r.original_transaction_id);snap=db.get(CheckoutSnapshot,tx.checkout_id) if tx else None
        intent=db.get(Intent,tx.intent_id) if tx else None
        candidates=[]
        if intent:
            allowed_variants={str(v).casefold() for v in json.loads(intent.allowed_variants_json or '[]')}
            products=db.scalars(select(Product).where(Product.merchant_id==merchant.id,Product.visible.is_(True)).order_by(Product.price_minor.asc())).all()
            for product in products:
                reasons=[]
                if intent.brand and product.brand.casefold()!=intent.brand.casefold():reasons.append('BRAND_OUTSIDE_AUTHORITY')
                if intent.category and product.category.casefold()!=intent.category.casefold():reasons.append('CATEGORY_OUTSIDE_AUTHORITY')
                if allowed_variants and product.variant.casefold() not in allowed_variants:reasons.append('VARIANT_OUTSIDE_AUTHORITY')
                if product.price_minor>intent.max_amount_minor:reasons.append('AMOUNT_OUTSIDE_AUTHORITY')
                if product.inventory<1:reasons.append('OUT_OF_STOCK')
                candidates.append({'sku':product.sku,'product':product.product,'brand':product.brand,'category':product.category,'variant':product.variant,'unit_price_minor':product.price_minor,'currency':product.currency,'inventory':product.inventory,'delivery_days':product.delivery_days,'eligible':not reasons,'reason_codes':reasons})
        items.append({'case_id':r.id,'original_transaction_id':r.original_transaction_id,'status':r.status,'attempts':r.attempts,'recovered_transaction_id':r.recovered_transaction_id,'last_reason':r.last_reason,'product':snap.product if snap else '', 'sku':snap.sku if snap else '', 'amount_minor':tx.amount_minor if tx else 0,'created_at':r.created_at,'authority':{'brand':intent.brand if intent else None,'category':intent.category if intent else None,'max_quantity':intent.max_quantity if intent else 0,'max_amount_minor':intent.max_amount_minor if intent else 0,'allowed_variants':list(allowed_variants) if intent else []},'candidates':candidates})
    return {'items':items,'open':sum(r.status=='OPEN' for r in rows),'recovered':sum(r.status=='RECOVERED' for r in rows),'recovered_gmv_minor':sum((db.get(Transaction,r.recovered_transaction_id).amount_minor if r.recovered_transaction_id and db.get(Transaction,r.recovered_transaction_id) else 0) for r in rows if r.status=='RECOVERED')}

@router.post('/recovery/{case_id}/execute',response_model=TransactionResponse)
def execute_recovery(case_id:str,payload:RecoveryRequest,merchant:Merchant=Depends(get_onboarded_merchant),db:Session=Depends(get_db)):
    case=db.get(RecoveryCase,case_id)
    if case is None or case.merchant_id!=merchant.id:raise HTTPException(404,'Recovery case not found')
    original=db.get(Transaction,case.original_transaction_id)
    if original is None or original.payment_state!='FAILED':raise HTTPException(409,'Authoritative payment state is not FAILED')
    policy=current_policy(db,merchant.id)
    if case.attempts>=policy.max_recovery_attempts:raise HTTPException(409,'Recovery attempt limit reached')
    intent=db.get(Intent,original.intent_id);mandate=db.get(Mandate,original.mandate_id)
    if not intent or not mandate:raise HTTPException(409,'Original authority evidence missing')
    snapshot=create_checkout_snapshot(db,merchant,payload.sku,payload.quantity)
    env=build_reference_envelope(db,merchant,mandate,snapshot)
    case.attempts+=1
    tx=evaluate_transaction(db,merchant,intent=intent,mandate=mandate,sku=payload.sku,quantity=payload.quantity,checkout_id=snapshot.id,signed_checkout_hash=env['checkout_hash'],agent_id=env['agent_id'],nonce=env['nonce'],timestamp=env['timestamp'],signature=env['signature'],idempotency_key=f'recovery_{case.id}_{case.attempts}_{uuid.uuid4().hex[:8]}',recovery_of_transaction_id=original.id)
    if tx.decision=='ALLOW':
        order=db.scalar(select(RazorpayOrder).where(RazorpayOrder.transaction_id==tx.id))
        if order is not None and order.mode=='LOCAL_TEST':
            apply_payment_event(db,tx,'CAPTURED',verified=False)
        else:
            case.last_reason='Authority approved; awaiting verified Razorpay Test payment'
    else:
        case.last_reason=', '.join(json.loads(tx.reason_codes_json or '[]')) or tx.decision
    db.commit();db.refresh(tx)
    return serialize_tx(db,tx)
