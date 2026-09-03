from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.discovery import _discovery
from app.core.dependencies import get_current_merchant
from app.db.session import get_db
from app.models import Merchant, MerchantPolicy
from app.schemas.onboarding import CompleteOnboardingResponse,IdentityResponse,OnboardingActionResponse
from app.schemas.readiness import ReadinessCheck,ReadinessResponse
from app.services.catalog import catalog_summary
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
import base64,hashlib
router=APIRouter(tags=['onboarding'])

def _readiness(db:Session,m:Merchant):
    summary=catalog_summary(db,m.id)
    p=db.scalar(select(MerchantPolicy).where(MerchantPolicy.merchant_id==m.id,MerchantPolicy.status=='PUBLISHED'))
    checks=[ReadinessCheck(name='payment_infrastructure',status='CONNECTED' if m.payment_test_connected else 'NOT_READY'),ReadinessCheck(name='agent_catalog',status='VALIDATED' if summary.skus>0 else 'NOT_READY'),ReadinessCheck(name='merchant_policy',status='PUBLISHED' if p else 'NOT_READY'),ReadinessCheck(name='merchant_identity',status='ACTIVE' if m.identity_active else 'NOT_READY'),ReadinessCheck(name='agent_discovery',status='ENABLED' if m.discovery_enabled else 'NOT_READY'),ReadinessCheck(name='intentlock_gateway',status='READY')]
    overall='AI_TRANSACTABLE' if all(c.status!='NOT_READY' for c in checks) else 'NOT_READY'
    return ReadinessResponse(merchant_id=m.id,overall=overall,checks=checks)

@router.post('/onboarding/payment/test',response_model=OnboardingActionResponse)
def payment_test(m:Merchant=Depends(get_current_merchant),db:Session=Depends(get_db)):
    m.payment_test_connected=True; db.commit(); return OnboardingActionResponse(status='CONNECTED',merchant_id=m.id,detail='Razorpay Test Mode rail marked ready for local hackathon development.')

@router.post('/onboarding/identity/provision',response_model=IdentityResponse)
def identity(m:Merchant=Depends(get_current_merchant),db:Session=Depends(get_db)):
    if not m.identity_active:
        priv=Ed25519PrivateKey.generate(); pub=priv.public_key().public_bytes(encoding=serialization.Encoding.Raw,format=serialization.PublicFormat.Raw)
        m.identity_algorithm='Ed25519'; m.identity_public_key=base64.urlsafe_b64encode(pub).decode().rstrip('='); m.identity_fingerprint='mk_'+hashlib.sha256(pub).hexdigest()[:16]; m.identity_active=True; db.commit()
    return IdentityResponse(merchant_id=m.id,merchant_name=m.name,algorithm=m.identity_algorithm or 'Ed25519',fingerprint=m.identity_fingerprint or '',status='ACTIVE')

@router.get('/onboarding/readiness',response_model=ReadinessResponse)
def readiness(m:Merchant=Depends(get_current_merchant),db:Session=Depends(get_db)): return _readiness(db,m)

@router.post('/onboarding/complete',response_model=CompleteOnboardingResponse)
def complete(m:Merchant=Depends(get_current_merchant),db:Session=Depends(get_db)):
    r=_readiness(db,m)
    if r.overall!='AI_TRANSACTABLE': raise HTTPException(409,'Onboarding is not ready to complete')
    m.onboarding_completed=True; m.status='ACTIVE'; db.commit()
    return CompleteOnboardingResponse(merchant_id=m.id,merchant_name=m.name,status='AI_TRANSACTABLE',onboarding_completed=True)
