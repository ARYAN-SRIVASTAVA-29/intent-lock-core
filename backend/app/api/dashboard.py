import json
import math
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from fastapi import APIRouter,Depends
from sqlalchemy import func,select
from sqlalchemy.orm import Session
from app.core.dependencies import get_onboarded_merchant
from app.db.session import get_db
from app.models import Agent,AuditEvent,CheckoutSnapshot,Merchant,Product,RazorpayOrder,RecoveryCase,Transaction
from app.services.agents import ensure_reference_agent
from app.services.audit import verify_chain
from app.services.catalog import catalog_summary
from app.core.config import get_settings

router=APIRouter(tags=['dashboard'])
settings=get_settings()

def money_minor(rows,states):return sum(t.amount_minor for t in rows if t.payment_state in states)

@router.get('/dashboard')
def dashboard(merchant:Merchant=Depends(get_onboarded_merchant),db:Session=Depends(get_db)):
    ensure_reference_agent(db,merchant.id);db.commit()
    txs=list(db.scalars(select(Transaction).where(Transaction.merchant_id==merchant.id).order_by(Transaction.created_at.desc())).all())
    agents=list(db.scalars(select(Agent).where(Agent.merchant_id==merchant.id)).all())
    recoveries=list(db.scalars(select(RecoveryCase).where(RecoveryCase.merchant_id==merchant.id)).all())
    audit=list(db.scalars(select(AuditEvent).where(AuditEvent.merchant_id==merchant.id).order_by(AuditEvent.sequence.desc()).limit(12)).all())
    inventory=list(db.scalars(select(Product).where(Product.merchant_id==merchant.id).order_by(Product.inventory.asc(),Product.product.asc())).all())
    catalog=catalog_summary(db,merchant.id).model_dump()
    captured=money_minor(txs,{'CAPTURED','RECOVERED'})
    recovered=money_minor(txs,{'RECOVERED'})
    blocked=[t for t in txs if t.decision=='BLOCKED']
    recovered_actions=[t for t in txs if t.payment_state=='RECOVERED']
    plain_allowed=[t for t in txs if t.decision=='ALLOW' and t.payment_state!='RECOVERED']
    replays=sum('REPLAY_DETECTED' in json.loads(t.reason_codes_json or '[]') or 'MANDATE_ALREADY_CONSUMED' in json.loads(t.reason_codes_json or '[]') for t in txs)
    payment_orders=list(db.scalars(select(RazorpayOrder).join(Transaction,RazorpayOrder.transaction_id==Transaction.id).where(Transaction.merchant_id==merchant.id)).all())
    order_tx_ids={o.transaction_id for o in payment_orders}
    critical_failures=sum(t.decision!='ALLOW' and t.id in order_tx_ids for t in txs) + (0 if verify_chain(db,merchant.id)[0] else 1)
    snapshots={tx.id:db.get(CheckoutSnapshot,tx.checkout_id) for tx in txs}
    rows=[]
    for tx in txs[:10]:
        snap=snapshots.get(tx.id)
        rows.append({'transaction_id':tx.id,'agent_id':tx.agent_id,'intent_id':tx.intent_id,'mandate_id':tx.mandate_id,'product':snap.product if snap else '','sku':snap.sku if snap else '','quantity':snap.quantity if snap else 0,'amount_minor':tx.amount_minor,'decision':tx.decision,'payment_state':tx.payment_state,'latency_ms':tx.latency_ms,'duplicate_count':tx.duplicate_count,'created_at':tx.created_at})
    ok,count,failed=verify_chain(db,merchant.id)
    webhook_state=('VERIFIED' if settings.razorpay_webhook_secret else ('NOT_CONFIGURED' if settings.razorpay_key_id and settings.razorpay_key_secret else 'LOCAL_SIMULATION'))
    paid_states={'AUTHORIZED','CAPTURED','RECOVERED'}
    captured_states={'CAPTURED','RECOVERED'}
    latencies=sorted(t.latency_ms for t in txs)
    p95_latency=latencies[max(0,math.ceil(len(latencies)*.95)-1)] if latencies else 0
    now=datetime.now(UTC)
    activity=[]
    for offset in range(6,-1,-1):
        day=(now-timedelta(days=offset)).date()
        day_rows=[t for t in txs if t.created_at.date()==day]
        activity.append({
            'date':day.isoformat(),
            'label':day.strftime('%a'),
            'total':len(day_rows),
            'allowed':sum(t.decision=='ALLOW' for t in day_rows),
            'blocked':sum(t.decision=='BLOCKED' for t in day_rows),
            'step_up':sum(t.decision=='STEP-UP' for t in day_rows),
            'captured_gmv_minor':money_minor(day_rows,captured_states),
        })
    product_activity=defaultdict(lambda:{'product':'','sku':'','actions':0,'committed_units':0,'captured_gmv_minor':0})
    for tx in txs:
        snap=snapshots.get(tx.id)
        if not snap:continue
        item=product_activity[snap.sku]
        item['product']=snap.product;item['sku']=snap.sku;item['actions']+=1
        if tx.payment_state in paid_states:item['committed_units']+=snap.quantity
        if tx.payment_state in captured_states:item['captured_gmv_minor']+=tx.amount_minor
    top_products=sorted(product_activity.values(),key=lambda item:(item['committed_units'],item['actions']),reverse=True)[:5]
    evaluated=len(txs)
    allowed_count=sum(t.decision=='ALLOW' for t in txs)
    order_count=len(payment_orders)
    authorized_count=sum(t.payment_state in paid_states for t in txs)
    captured_count=sum(t.payment_state in captured_states for t in txs)
    failed_count=sum(t.payment_state=='FAILED' for t in txs)
    return {
      'merchant':{'merchant_id':merchant.id,'merchant_name':merchant.name,'environment':merchant.environment,'discovery_enabled':merchant.discovery_enabled,'identity_active':merchant.identity_active,'catalog':catalog},
      'commerce':{'captured_gmv_minor':captured,'economic_actions':len(txs),'discoverable_skus':catalog['visible_skus'],'registered_agents':len(agents),'recovered_gmv_minor':recovered},
      'enforcement':{'allowed':len(plain_allowed),'blocked':len(blocked),'step_up':sum(t.decision=='STEP-UP' for t in txs),'recovered':len(recovered_actions),'unsafe_gmv_minor':sum(t.amount_minor for t in blocked),'blocked_before_razorpay':sum(t.decision=='BLOCKED' and t.razorpay_api_calls==0 for t in txs),'duplicates_prevented':sum(t.duplicate_count for t in txs),'replays_rejected':replays,'critical_failures':critical_failures},
      'transactions':rows,
      'live_events':[{'event_type':e.event_type,'actor':e.actor,'transaction_id':e.transaction_id,'created_at':e.created_at,'event_hash':e.event_hash} for e in audit],
      'agents':{'registered':len(agents),'verified':sum(a.trust=='VERIFIED' for a in agents),'step_up':sum(a.trust=='STEP_UP' for a in agents),'suspended':sum(a.status=='SUSPENDED' for a in agents),'items':[{'agent_id':a.agent_id,'provider':a.provider,'trust':a.trust,'status':a.status,'violations':a.violations,'last_seen_at':a.last_seen_at} for a in agents[:4]]},
      'payments':{'open_recovery_cases':sum(r.status=='OPEN' for r in recoveries),'recovered_cases':sum(r.status=='RECOVERED' for r in recoveries),'captured_gmv_minor':captured,'recovered_gmv_minor':recovered,'webhook_state':webhook_state,'mode':'RAZORPAY_TEST' if settings.razorpay_key_id and settings.razorpay_key_secret else 'LOCAL_TEST'},
      'audit':{'integrity':'VERIFIED' if ok else 'TAMPERED','events':count,'failed_sequence':failed},
      'operations':{
        'inventory':{
          'total_units':sum(p.inventory for p in inventory),
          'inventory_value_minor':sum(p.inventory*p.price_minor for p in inventory),
          'sellable_skus':sum(p.visible and p.inventory>0 for p in inventory),
          'low_stock_skus':sum(p.visible and 0<p.inventory<=5 for p in inventory),
          'out_of_stock_skus':sum(p.visible and p.inventory==0 for p in inventory),
          'committed_units':sum((snapshots[t.id].quantity if snapshots.get(t.id) else 0) for t in txs if t.payment_state in paid_states),
          'items':[{'sku':p.sku,'product':p.product,'inventory':p.inventory,'status':'OUT_OF_STOCK' if p.inventory==0 else ('LOW_STOCK' if p.inventory<=5 else 'HEALTHY')} for p in inventory[:6]],
        },
        'funnel':{
          'evaluated':evaluated,
          'allowed':allowed_count,
          'orders_created':order_count,
          'authorized':authorized_count,
          'captured':captured_count,
          'failed':failed_count,
          'allow_rate':round(allowed_count/evaluated*100,1) if evaluated else 0,
          'payment_completion_rate':round(captured_count/order_count*100,1) if order_count else 0,
        },
        'performance':{
          'average_latency_ms':round(sum(latencies)/len(latencies),1) if latencies else 0,
          'p95_latency_ms':p95_latency,
          'actions_24h':sum((now-(t.created_at.replace(tzinfo=UTC) if t.created_at.tzinfo is None else t.created_at.astimezone(UTC)))<=timedelta(hours=24) for t in txs),
          'critical_failures':critical_failures,
        },
        'activity_7d':activity,
        'top_products':top_products,
      },
    }
