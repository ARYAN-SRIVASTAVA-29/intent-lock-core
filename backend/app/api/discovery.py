from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.dependencies import get_current_merchant
from app.db.session import get_db
from app.models import Merchant, MerchantPolicy
from app.schemas.discovery import DiscoveryResponse,DiscoveryTestResponse,DiscoveryTestStep,ProtocolStatus
from app.services.catalog import catalog_summary
router=APIRouter(tags=['agent-commerce'])

def _discovery(db:Session,merchant_id:str)->DiscoveryResponse:
    merchant=db.get(Merchant,merchant_id)
    if merchant is None: raise HTTPException(404,'Merchant not found')
    policy=db.scalar(select(MerchantPolicy).where(MerchantPolicy.merchant_id==merchant_id,MerchantPolicy.status=='PUBLISHED'))
    summary=catalog_summary(db,merchant_id)
    ready=merchant.discovery_enabled and merchant.payment_test_connected and merchant.identity_active and summary.visible_skus>0 and policy is not None
    base=f'/api/v1/agent-commerce/merchants/{merchant.id}'
    return DiscoveryResponse(merchant_id=merchant.id,merchant_name=merchant.name,status='AI_TRANSACTABLE' if ready else 'NOT_READY',environment=merchant.environment,catalog_endpoint=f'{base}/catalog',policy_endpoint=f'{base}/policy',checkout_endpoint=f'{base}/checkouts',transaction_endpoint=f'{base}/transactions',discovery_endpoint=f'{base}/discovery',products=summary.products,skus=summary.skus,brands=summary.brands,categories=summary.categories,policy_version=policy.version if policy else 'none',protocols=ProtocolStatus(rest='ACTIVE',acp='PLANNED',ucp='PLANNED',mcp='PLANNED',x402='PLANNED'))

def _checks(discovery:DiscoveryResponse,merchant:Merchant):
    return [DiscoveryTestStep(step='merchant_resolved',status='PASS'),DiscoveryTestStep(step='payment_test_mode',status='PASS' if merchant.payment_test_connected else 'FAIL'),DiscoveryTestStep(step='catalog_fetched',status='PASS' if discovery.skus>0 else 'FAIL'),DiscoveryTestStep(step='policy_advertised',status='PASS' if discovery.policy_version!='none' else 'FAIL'),DiscoveryTestStep(step='merchant_identity',status='PASS' if merchant.identity_active else 'FAIL'),DiscoveryTestStep(step='checkout_capability',status='PASS'),DiscoveryTestStep(step='transaction_capability',status='PASS'),DiscoveryTestStep(step='rest_adapter',status='PASS')]

@router.get('/agent-commerce/merchants/{merchant_id}/discovery',response_model=DiscoveryResponse)
def public_discovery(merchant_id:str,db:Session=Depends(get_db)): return _discovery(db,merchant_id)

@router.get('/agent-commerce/discovery',response_model=DiscoveryResponse)
def current_discovery(merchant:Merchant=Depends(get_current_merchant),db:Session=Depends(get_db)): return _discovery(db,merchant.id)

@router.post('/agent-commerce/discovery/test',response_model=DiscoveryTestResponse)
def test_discovery(merchant:Merchant=Depends(get_current_merchant),db:Session=Depends(get_db)):
    # Discovery is enabled only after all prerequisite checks pass.
    merchant.discovery_enabled=True; db.flush()
    d=_discovery(db,merchant.id); checks=_checks(d,merchant)
    result='DISCOVERABLE' if all(c.status=='PASS' for c in checks) else 'NOT_READY'
    if result!='DISCOVERABLE': merchant.discovery_enabled=False
    db.commit()
    return DiscoveryTestResponse(result=result,merchant_id=merchant.id,checks=checks)
