import hashlib
import hmac
import json

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.dependencies import get_onboarded_merchant
from app.db.session import get_db
from app.models import Merchant, RazorpayOrder, Transaction
from app.schemas.transactions import PaymentVerifyRequest, TransactionResponse
from app.api.transactions import serialize_tx
from app.services.payments import apply_payment_event, verify_checkout_signature

router=APIRouter(tags=["payments"])
settings=get_settings()


@router.get('/payments/config')
def payment_config():
    credentials_present=bool(settings.razorpay_key_id and settings.razorpay_key_secret)
    test_key_valid=bool(credentials_present and settings.razorpay_key_id.startswith('rzp_test_'))
    partial_credentials=bool(settings.razorpay_key_id) != bool(settings.razorpay_key_secret)
    return {
        'razorpay_enabled':test_key_valid,
        'key_id':settings.razorpay_key_id if test_key_valid else None,
        'key_id_masked':f"{settings.razorpay_key_id[:12]}…{settings.razorpay_key_id[-4:]}" if test_key_valid else None,
        'mode':'RAZORPAY_TEST' if test_key_valid else ('CONFIG_ERROR' if credentials_present or partial_credentials else 'LOCAL_TEST'),
        'credentials_state':'CONNECTED' if test_key_valid else ('INCOMPLETE' if partial_credentials else ('INVALID_TEST_KEY' if credentials_present else 'NOT_CONFIGURED')),
        'webhook_ready':bool(test_key_valid and settings.razorpay_webhook_secret),
        'checkout_ready':test_key_valid,
    }

@router.post('/payments/verify',response_model=TransactionResponse)
def verify_payment(payload:PaymentVerifyRequest,merchant:Merchant=Depends(get_onboarded_merchant),db:Session=Depends(get_db)):
    order=db.scalar(select(RazorpayOrder).where(RazorpayOrder.razorpay_order_id==payload.razorpay_order_id))
    if order is None: raise HTTPException(404,'Razorpay order not found')
    tx=db.get(Transaction,order.transaction_id)
    if tx is None or tx.merchant_id!=merchant.id: raise HTTPException(404,'Transaction not found')
    if order.mode != 'RAZORPAY_TEST':
        raise HTTPException(409,'Checkout signature verification is only valid for RAZORPAY_TEST orders')
    if not verify_checkout_signature(payload.razorpay_order_id,payload.razorpay_payment_id,payload.razorpay_signature):
        raise HTTPException(400,'Razorpay signature verification failed')
    try:
        apply_payment_event(db,tx,'AUTHORIZED',payload.razorpay_payment_id,verified=True)
    except ValueError as exc:
        raise HTTPException(409,str(exc)) from exc
    db.commit();db.refresh(tx)
    return serialize_tx(db,tx)

@router.post('/payments/webhook')
async def webhook(request:Request,x_razorpay_signature:str|None=Header(default=None),db:Session=Depends(get_db)):
    body=await request.body()
    if not settings.razorpay_webhook_secret:
        raise HTTPException(503,'Razorpay webhook secret is not configured')
    expected=hmac.new(settings.razorpay_webhook_secret.encode(),body,hashlib.sha256).hexdigest()
    if not x_razorpay_signature or not hmac.compare_digest(expected,x_razorpay_signature):
        raise HTTPException(400,'Webhook signature verification failed')
    data=json.loads(body or b'{}')
    event=data.get('event','')
    entity=((data.get('payload') or {}).get('payment') or {}).get('entity') or {}
    order_id=entity.get('order_id')
    if not order_id:return {'ok':True,'ignored':True}
    order=db.scalar(select(RazorpayOrder).where(RazorpayOrder.razorpay_order_id==order_id))
    if order is None:return {'ok':True,'ignored':True}
    tx=db.get(Transaction,order.transaction_id)
    if tx is None:return {'ok':True,'ignored':True}
    outcome={'payment.captured':'CAPTURED','payment.failed':'FAILED','payment.authorized':'AUTHORIZED','order.paid':'CAPTURED'}.get(event)
    if outcome:
        if entity.get('amount') is not None and int(entity['amount']) != order.amount_minor:
            raise HTTPException(409,'Webhook amount does not match the authorized order')
        if entity.get('currency') and entity['currency'] != order.currency:
            raise HTTPException(409,'Webhook currency does not match the authorized order')
        try:
            apply_payment_event(db,tx,outcome,entity.get('id'),verified=True)
        except ValueError as exc:
            raise HTTPException(409,str(exc)) from exc
        db.commit()
    return {'ok':True,'event':event,'transaction_id':tx.id}
