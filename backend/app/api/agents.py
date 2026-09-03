import hashlib
from datetime import UTC,datetime
from fastapi import APIRouter,Depends,HTTPException,status
from pydantic import BaseModel,Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from app.core.dependencies import get_onboarded_merchant
from app.db.session import get_db
from app.models import Agent,Merchant
from app.services.agents import ensure_reference_agent

router=APIRouter(tags=["agents"])

class AgentRegisterRequest(BaseModel):
    agent_id:str=Field(min_length=3,max_length=96)
    provider:str=Field(default='External Agent',max_length=96)
    public_key:str


def _fingerprint(public_key:str)->str:return hashlib.sha256(public_key.encode()).hexdigest()[:20]

def _validate_key(pem:str):
    try:
        key=serialization.load_pem_public_key(pem.encode())
        if not isinstance(key,Ed25519PublicKey):raise ValueError
    except Exception as exc:raise HTTPException(400,'public_key must be an Ed25519 PEM public key') from exc

@router.post('/agents',status_code=status.HTTP_201_CREATED)
def register_agent(payload:AgentRegisterRequest,merchant:Merchant=Depends(get_onboarded_merchant),db:Session=Depends(get_db)):
    _validate_key(payload.public_key)
    existing=db.scalar(select(Agent).where(Agent.merchant_id==merchant.id,Agent.agent_id==payload.agent_id))
    if existing:raise HTTPException(409,'Agent ID already registered for this merchant')
    agent=Agent(merchant_id=merchant.id,agent_id=payload.agent_id,provider=payload.provider,trust='VERIFIED',status='ACTIVE',algorithm='Ed25519',public_key=payload.public_key,last_seen_at=None)
    db.add(agent);db.commit();db.refresh(agent)
    return {'agent_id':agent.agent_id,'provider':agent.provider,'trust':agent.trust,'status':agent.status,'algorithm':agent.algorithm,'fingerprint':_fingerprint(agent.public_key)}

@router.get('/agents')
def list_agents(merchant:Merchant=Depends(get_onboarded_merchant),db:Session=Depends(get_db)):
    ensure_reference_agent(db,merchant.id);db.commit()
    rows=db.scalars(select(Agent).where(Agent.merchant_id==merchant.id).order_by(Agent.created_at)).all()
    return {"items":[{"agent_id":a.agent_id,"provider":a.provider,"trust":a.trust,"status":a.status,"algorithm":a.algorithm,"violations":a.violations,"last_seen_at":a.last_seen_at,"fingerprint":_fingerprint(a.public_key)} for a in rows],"registered":len(rows),"verified":sum(a.trust=='VERIFIED' for a in rows),"step_up":sum(a.trust=='STEP_UP' for a in rows),"suspended":sum(a.status=='SUSPENDED' for a in rows)}
