'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { Activity, AlertTriangle, ArrowRight, Bot, Boxes, CheckCircle2, CircleDollarSign, Clock3, CreditCard, PackageCheck, RefreshCw, ShieldCheck, TrendingUp, Zap } from 'lucide-react'
import { formatFreshness, formatMinorCurrency, intentLockApi, type DashboardApi, type MerchantResponse } from '@/lib/intentlock-api'

const ago=(value:string)=>{const ms=Date.now()-new Date(value).getTime();const minutes=Math.max(0,Math.floor(ms/60000));return minutes<1?'now':minutes<60?`${minutes}m ago`:`${Math.floor(minutes/60)}h ago`}
const tone=(value:string)=>value==='ALLOW'||value==='CAPTURED'||value==='RECOVERED'||value==='VERIFIED'||value==='HEALTHY'?'success':value==='BLOCKED'||value==='FAILED'||value==='TAMPERED'||value==='OUT_OF_STOCK'?'danger':value==='STEP-UP'||value==='AUTHORIZED'||value==='LOW_STOCK'?'warning':'neutral'
const pct=(value:number,total:number)=>total?Math.max(2,Math.round(value/total*100)):0

function DashboardLoader(){return <div className="control-room-loading" aria-label="Loading merchant control room"><div className="loader-command"><span/><span/><span/></div><div className="loader-metrics">{Array.from({length:6},(_,i)=><span key={i}/>)}</div><div className="loader-panels"><span/><span/><span/></div></div>}

export function PlatformDashboard({Shell}:{Shell:React.ComponentType<{children:React.ReactNode;title:string;subtitle?:string;compact?:boolean}>}){
  const [merchant,setMerchant]=useState<MerchantResponse|null>(null)
  const [data,setData]=useState<DashboardApi|null>(null)
  const [error,setError]=useState('')
  const [loading,setLoading]=useState(true)
  const load=async()=>{setLoading(true);try{const [m,d]=await Promise.all([intentLockApi.merchant(),intentLockApi.dashboard()]);setMerchant(m);setData(d);setError('')}catch(e){setError(e instanceof Error?e.message:'Unable to load merchant operations')}finally{setLoading(false)}}
  useEffect(()=>{load()},[])
  if(loading&&!data)return <Shell title="Dashboard" compact><DashboardLoader/></Shell>

  const commerce=data?.commerce??{captured_gmv_minor:0,economic_actions:0,discoverable_skus:merchant?.catalog.visible_skus??0,registered_agents:0,recovered_gmv_minor:0}
  const enforcement=data?.enforcement??{allowed:0,blocked:0,step_up:0,recovered:0,unsafe_gmv_minor:0,blocked_before_razorpay:0,duplicates_prevented:0,replays_rejected:0,critical_failures:0}
  const ops=data?.operations
  const transactions=data?.transactions.slice(0,8)??[]
  const decisions=enforcement.allowed+enforcement.blocked+enforcement.step_up
  const paymentMode=data?.payments.mode??'LOCAL_TEST'
  const maxActivity=Math.max(1,...(ops?.activity_7d.map(day=>day.total)??[1]))
  const readiness=[['Discovery',merchant?.discovery_enabled?'Active':'Not ready'],['Catalog',merchant?`${merchant.catalog.visible_skus} SKUs live`:'Loading'],['IntentLock','Healthy'],['Payment',paymentMode==='RAZORPAY_TEST'?'Razorpay Test':'Local Test'],['Audit',data?.audit.integrity??'Checking']]
  const funnel=ops?.funnel
  const stages=[['Evaluated',funnel?.evaluated??0],['Allowed',funnel?.allowed??0],['Orders',funnel?.orders_created??0],['Authorized',funnel?.authorized??0],['Captured',funnel?.captured??0]] as const
  return <Shell title="Dashboard" compact><div className="control-room-dashboard">
    <header className="control-room-title"><div><span className="ops-eyebrow">LIVE MERCHANT CONTROL ROOM</span><h1>Welcome back, <em>{merchant?.merchant_name??'Merchant'}</em></h1><p>Authority, payments, inventory and agent activity in one operational view.</p></div><div className="control-room-actions"><button onClick={load} disabled={loading}><RefreshCw className={loading?'spin':''} size={15}/>{loading?'Refreshing':'Refresh data'}</button><Link href="/attack-lab"><Zap size={15}/>Attack Lab</Link><Link className="primary" href="/buyer-demo"><Bot size={15}/>Run Reference Buyer</Link></div></header>
    {error&&<div className="ops-alert danger"><AlertTriangle size={16}/>{error}</div>}

    <section className="control-status-rail" aria-label="System readiness">{readiness.map(([label,value])=><div key={label}><CheckCircle2 size={15}/><span>{label}</span><b>{value}</b></div>)}</section>

    <section className="control-metrics">
      <article><span>Captured GMV</span><strong>{formatMinorCurrency(commerce.captured_gmv_minor)}</strong><small><TrendingUp size={12}/>verified settlements</small></article>
      <article><span>Economic actions</span><strong>{commerce.economic_actions}</strong><small>{ops?.performance.actions_24h??0} during last 24h</small></article>
      <article><span>Allow rate</span><strong>{ops?.funnel.allow_rate??0}%</strong><small>{enforcement.allowed} of {decisions} decisions allowed</small></article>
      <article><span>Available inventory</span><strong>{ops?.inventory.total_units??0}</strong><small>{ops?.inventory.sellable_skus??0} sellable SKUs</small></article>
      <article><span>Unsafe GMV stopped</span><strong>{formatMinorCurrency(enforcement.unsafe_gmv_minor)}</strong><small>{enforcement.blocked_before_razorpay} blocked before Razorpay</small></article>
      <article><span>Kernel p95</span><strong>{ops?.performance.p95_latency_ms??0}<i>ms</i></strong><small>{ops?.performance.average_latency_ms??0}ms average</small></article>
    </section>

    <section className="control-primary-grid">
      <article className="control-panel transaction-monitor"><div className="control-panel-head"><div><span>TRANSACTION MONITOR</span><h2>Recent economic actions</h2></div><Link href="/transactions">Open ledger <ArrowRight size={13}/></Link></div><div className="control-table"><table><thead><tr><th>Transaction</th><th>Product / agent</th><th>Amount</th><th>Decision</th><th>Payment</th><th>Latency</th><th>Age</th></tr></thead><tbody>{transactions.map(tx=><tr key={tx.transaction_id}><td><Link href={`/transactions/${tx.transaction_id}`}>{tx.transaction_id}</Link><small>{tx.intent_id}</small></td><td><b>{tx.product} × {tx.quantity}</b><small>{tx.agent_id}</small></td><td><b>{formatMinorCurrency(tx.amount_minor)}</b></td><td><span className={`control-badge ${tone(tx.decision)}`}>{tx.decision}</span></td><td><span className={`control-badge ${tone(tx.payment_state)}`}>{tx.payment_state.replaceAll('_',' ')}</span></td><td>{tx.latency_ms}ms</td><td>{ago(tx.created_at)}</td></tr>)}{!transactions.length&&<tr><td colSpan={7} className="control-empty">No actions recorded. Run the Reference Buyer to create the first governed transaction.</td></tr>}</tbody></table></div></article>
      <article className="control-panel defense-monitor"><div className="control-panel-head"><div><span>AUTHORITY ENFORCEMENT</span><h2>Decision posture</h2></div><ShieldCheck size={18}/></div><div className="decision-score"><strong>{decisions}</strong><span>evaluated actions</span></div><div className="decision-meter"><i className="allow" style={{width:`${pct(enforcement.allowed,decisions)}%`}}/><i className="block" style={{width:`${pct(enforcement.blocked,decisions)}%`}}/><i className="step" style={{width:`${pct(enforcement.step_up,decisions)}%`}}/></div><div className="decision-ledger"><div><span><i className="allow"/>Allowed</span><b>{enforcement.allowed}</b></div><div><span><i className="block"/>Blocked</span><b>{enforcement.blocked}</b></div><div><span><i className="step"/>Step-up</span><b>{enforcement.step_up}</b></div><div><span>Duplicates contained</span><b>{enforcement.duplicates_prevented}</b></div><div><span>Replay attempts rejected</span><b>{enforcement.replays_rejected}</b></div><div><span>Critical control failures</span><b className={enforcement.critical_failures?'danger-text':'success-text'}>{enforcement.critical_failures}</b></div></div><Link className="panel-link" href="/attack-lab">Inspect the financial boundary <ArrowRight size={13}/></Link></article>
    </section>

    <section className="control-analytics-grid">
      <article className="control-panel activity-monitor"><div className="control-panel-head"><div><span>7-DAY ACTIVITY</span><h2>Agent action volume</h2></div><Activity size={18}/></div><div className="activity-chart">{(ops?.activity_7d??[]).map(day=><div className="activity-day" key={day.date}><div className="activity-columns"><i className="allow" style={{height:`${Math.max(3,day.allowed/maxActivity*100)}%`}}/><i className="block" style={{height:`${Math.max(3,day.blocked/maxActivity*100)}%`}}/><i className="step" style={{height:`${Math.max(3,day.step_up/maxActivity*100)}%`}}/></div><b>{day.total}</b><span>{day.label}</span></div>)}</div><div className="chart-legend"><span><i className="allow"/>Allowed</span><span><i className="block"/>Blocked</span><span><i className="step"/>Step-up</span></div></article>
      <article className="control-panel funnel-monitor"><div className="control-panel-head"><div><span>COMMERCE FUNNEL</span><h2>Intent to settlement</h2></div><CircleDollarSign size={18}/></div><div className="funnel-list">{stages.map(([label,value],index)=><div key={label}><span>{index+1}</span><b>{label}</b><i><em style={{width:`${pct(value,funnel?.evaluated??0)}%`}}/></i><strong>{value}</strong></div>)}</div><div className="funnel-footer"><span>Completion rate</span><strong>{funnel?.payment_completion_rate??0}%</strong></div></article>
      <article className="control-panel inventory-monitor"><div className="control-panel-head"><div><span>INVENTORY INTELLIGENCE</span><h2>Availability watch</h2></div><PackageCheck size={18}/></div><div className="inventory-summary"><span><b>{ops?.inventory.committed_units??0}</b>units committed</span><span><b>{ops?.inventory.low_stock_skus??0}</b>low stock</span><span><b>{ops?.inventory.out_of_stock_skus??0}</b>out of stock</span></div><div className="inventory-list">{(ops?.inventory.items??[]).slice(0,4).map(item=><div key={item.sku}><span><b>{item.product}</b><small>{item.sku}</small></span><strong>{item.inventory}</strong><em className={tone(item.status)}>{item.status.replaceAll('_',' ')}</em></div>)}</div><Link className="panel-link" href="/catalog">Manage catalog inventory <ArrowRight size={13}/></Link></article>
    </section>

    <section className="control-secondary-grid">
      <article className="control-panel audit-monitor"><div className="control-panel-head"><div><span>TAMPER-EVIDENT STREAM</span><h2>Live audit events</h2></div><Link href="/audit-log">Verify chain <ArrowRight size={13}/></Link></div><div className="audit-stream">{(data?.live_events??[]).slice(0,7).map(event=><div key={event.event_hash}><i className={event.event_type.includes('BLOCK')||event.event_type.includes('FAIL')?'danger':''}/><span><b>{event.event_type.replaceAll('_',' ')}</b><small>{event.actor} · hash {event.event_hash.slice(0,10)}…</small></span><time>{ago(event.created_at)}</time></div>)}</div></article>
      <article className="control-panel product-monitor"><div className="control-panel-head"><div><span>PRODUCT OPERATIONS</span><h2>Top catalog activity</h2></div><Boxes size={18}/></div><div className="product-activity">{(ops?.top_products??[]).map((item,index)=><div key={item.sku}><span>{String(index+1).padStart(2,'0')}</span><div><b>{item.product}</b><small>{item.sku}</small></div><strong>{item.committed_units}<small>units</small></strong><em>{item.actions} actions</em></div>)}{!ops?.top_products.length&&<p>No product activity yet.</p>}</div></article>
      <article className="control-panel infrastructure-monitor"><div className="control-panel-head"><div><span>PLATFORM HEALTH</span><h2>Operational readiness</h2></div><CheckCircle2 size={18}/></div><div className="infrastructure-list"><Link href="/payment-setup"><CreditCard/><span><b>{paymentMode.replaceAll('_',' ')}</b><small>Webhook: {data?.payments.webhook_state??'checking'}</small></span><ArrowRight/></Link><Link href="/catalog"><Boxes/><span><b>{merchant?.catalog.visible_skus??0} discoverable SKUs</b><small>Synced {formatFreshness(merchant?.catalog.last_updated_at??null)}</small></span><ArrowRight/></Link><Link href="/agents"><Bot/><span><b>{commerce.registered_agents} registered agents</b><small>{data?.agents.verified??0} cryptographically verified</small></span><ArrowRight/></Link><Link href="/recovery"><Clock3/><span><b>{data?.payments.open_recovery_cases??0} recovery cases</b><small>{data?.payments.recovered_cases??0} completed recoveries</small></span><ArrowRight/></Link></div></article>
    </section>
  </div></Shell>
}

export default PlatformDashboard
