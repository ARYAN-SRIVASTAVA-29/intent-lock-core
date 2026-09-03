from fastapi import APIRouter,Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.dependencies import get_onboarded_merchant
from app.db.session import get_db
from app.models import AuditEvent,Merchant
from app.services.audit import audit_payload,verify_chain
router=APIRouter(tags=['audit'])

@router.get('/audit')
def audit_events(merchant:Merchant=Depends(get_onboarded_merchant),db:Session=Depends(get_db)):
    rows=db.scalars(select(AuditEvent).where(AuditEvent.merchant_id==merchant.id).order_by(AuditEvent.sequence.desc()).limit(200)).all()
    ok,count,failed=verify_chain(db,merchant.id)
    return {'integrity':'VERIFIED' if ok else 'TAMPERED','count':count,'failed_sequence':failed,'items':[audit_payload(r) for r in reversed(rows)]}

@router.post('/audit/verify')
def verify_audit(merchant:Merchant=Depends(get_onboarded_merchant),db:Session=Depends(get_db)):
    ok,count,failed=verify_chain(db,merchant.id)
    return {'verified':ok,'count':count,'failed_sequence':failed}
