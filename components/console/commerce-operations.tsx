'use client'

import { useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { AlertTriangle, ArrowRight, Bot, Check, CheckCircle2, CircleDollarSign, Copy, CreditCard, ExternalLink, FileCheck2, LockKeyhole, PackageCheck, RefreshCw, RotateCcw, Search, ShieldCheck, Sparkles, Zap } from 'lucide-react'
import { Shell } from '@/components/intentlock-app'
import { formatMinorCurrency, intentLockApi, type AttackApi, type AttackConfigApi, type AttackPayload, type BuyerMatchApi, type BuyerPlanApi, type PaymentConfigApi, type RecoveryApi, type RecoveryCandidateApi, type TransactionApi } from '@/lib/intentlock-api'

const cx=(...values:Array<string|false|undefined>)=>values.filter(Boolean).join(' ')

async function loadRazorpayScript(){
  if((window as any).Razorpay)return
  await new Promise<void>((resolve,reject)=>{const script=document.createElement('script');script.src='https://checkout.razorpay.com/v1/checkout.js';script.onload=()=>resolve();script.onerror=()=>reject(new Error('Unable to load Razorpay Checkout'));document.body.appendChild(script)})
}

async function completePayment(current:TransactionApi,config:PaymentConfigApi){
  if(!config.razorpay_enabled||current.payment_mode==='LOCAL_TEST')return intentLockApi.simulatePayment(current.transaction_id,'CAPTURED')
  await loadRazorpayScript()
  return new Promise<TransactionApi>((resolve,reject)=>{
    const checkout=new (window as any).Razorpay({
      key:config.key_id,
      amount:current.amount_minor,
      currency:current.currency,
      order_id:current.payment_order_id,
      name:'IntentLock',
      description:`${current.product} · authorized agent purchase`,
      theme:{color:'#3157d5'},
      handler:async(response:any)=>{try{resolve(await intentLockApi.verifyPayment({razorpay_order_id:response.razorpay_order_id,razorpay_payment_id:response.razorpay_payment_id,razorpay_signature:response.razorpay_signature}))}catch(error){reject(error)}},
      modal:{ondismiss:()=>reject(new Error('Razorpay Checkout was closed before payment'))},
    })
    checkout.open()
  })
}

function DecisionBadge({value}:{value:string}){return <span className={cx('ops-badge',value==='ALLOW'||value==='CAPTURED'||value==='RECOVERED'||value==='CONNECTED'?'success':value==='BLOCKED'||value==='FAILED'||value.includes('ERROR')?'danger':value==='STEP-UP'||value==='AUTHORIZED'?'warning':'neutral')}>{value.replaceAll('_',' ')}</span>}

export function ReferenceBuyerConsole(){
  const [merchantName,setMerchantName]=useState('Merchant')
  const [request,setRequest]=useState('Show me all phones under ₹50,000')
  const [plan,setPlan]=useState<BuyerPlanApi|null>(null)
  const [selectedSku,setSelectedSku]=useState('')
  const [transaction,setTransaction]=useState<TransactionApi|null>(null)
  const [payment,setPayment]=useState<PaymentConfigApi|null>(null)
  const [busy,setBusy]=useState(false)
  const [error,setError]=useState('')
  useEffect(()=>{Promise.all([intentLockApi.merchant(),intentLockApi.paymentConfig()]).then(([m,p])=>{setMerchantName(m.merchant_name);setPayment(p)}).catch(e=>setError(e instanceof Error?e.message:'Unable to initialise Reference Buyer'))},[])
  const selected=useMemo(()=>plan?.matches.find(item=>item.sku===selectedSku)??plan?.matches[0]??null,[plan,selectedSku])
  const makePlan=async()=>{setBusy(true);setError('');setTransaction(null);try{const next=await intentLockApi.buyerPlan(request);setPlan(next);setSelectedSku(next.recommended_sku)}catch(e){setError(e instanceof Error?e.message:'Buyer planning failed')}finally{setBusy(false)}}
  const authorize=async()=>{if(!plan||!selected)return;setBusy(true);setError('');try{let tx=await intentLockApi.runDemoTransaction({sku:selected.sku,quantity:selected.quantity,max_quantity:selected.quantity,max_amount_minor:plan.max_amount_minor,natural_language:plan.request});if(tx.decision==='ALLOW'&&payment)tx=await completePayment(tx,payment);setTransaction(tx);if(tx.inventory_after!==null&&['AUTHORIZED','CAPTURED','RECOVERED'].includes(tx.payment_state))setPlan(current=>current?{...current,matches:current.matches.map(match=>match.sku===tx.sku?{...match,inventory:tx.inventory_after??match.inventory}:match)}:current)}catch(e){setError(e instanceof Error?e.message:'Purchase execution failed')}finally{setBusy(false)}}
  const failLocally=async()=>{if(!plan||!selected)return;setBusy(true);setError('');try{if(payment?.mode!=='LOCAL_TEST')throw new Error('Failure simulation is only available in LOCAL_TEST. Use a Razorpay Test failure method when connected.');let tx=await intentLockApi.runDemoTransaction({sku:selected.sku,quantity:selected.quantity,max_quantity:selected.quantity,max_amount_minor:plan.max_amount_minor,natural_language:plan.request});if(tx.decision==='ALLOW')tx=await intentLockApi.simulatePayment(tx.transaction_id,'FAILED');setTransaction(tx)}catch(e){setError(e instanceof Error?e.message:'Failure simulation failed')}finally{setBusy(false)}}
  return <Shell title="Reference Buyer" compact>
    <header className="operation-pagebar"><div><span className="ops-eyebrow"><Bot size={14}/> VERIFIED COMMERCE AGENT</span><h1>Reference Buyer</h1><p>Search the live catalog, compare eligible products and authorize one exact purchase.</p></div><div className="operation-page-actions"><Link href="/dashboard">← Control room</Link><div className="payment-connection"><span>Payment rail</span><DecisionBadge value={payment?.mode??'LOADING'}/></div></div></header>
    {busy&&<div className="operation-progress"><i/><span>{plan?'Evaluating authority and payment boundary…':'Searching the merchant catalog…'}</span></div>}
    <div className="buyer-workspace">
      <section className="ops-surface buyer-results">
        <form className="buyer-query" onSubmit={e=>{e.preventDefault();makePlan()}}><Search size={18}/><input aria-label="Shopping request" value={request} onChange={e=>setRequest(e.target.value)} placeholder="I want a phone under ₹50,000"/><button disabled={busy}>{busy?'Searching…':'Search catalog'}</button></form>
        {error&&<div className="ops-alert danger"><AlertTriangle size={16}/>{error}</div>}
        {!plan&&!busy&&<div className="ops-empty"><Sparkles size={22}/><strong>Ask a broad shopping question</strong><span>The buyer will return every eligible match, compare them, and recommend one. It cannot authorize or pay without you.</span></div>}
        {plan&&<><div className="result-heading"><div><strong>{plan.matches.length} eligible matches</strong><span>{plan.explanation}</span></div><span>{plan.planning_mode.replaceAll('_',' ')}</span></div><div className="match-table" role="radiogroup" aria-label="Eligible products">{plan.matches.map(match=><button type="button" role="radio" aria-checked={selected?.sku===match.sku} className={cx('match-row',selected?.sku===match.sku&&'selected')} key={match.sku} onClick={()=>{setSelectedSku(match.sku);setTransaction(null)}}><span className="match-radio"/><span className="match-product"><strong>{match.product}</strong><small>{match.brand} · {match.variant} · {match.sku}</small></span><span><strong>{formatMinorCurrency(match.total_minor,match.currency)}</strong><small>{match.inventory} available · {match.delivery_days}d delivery</small></span><span className="fit-score"><b>{match.fit_score}%</b><small>{match.recommendation_label}</small></span></button>)}</div></>}
      </section>
      <aside className="ops-surface buyer-authority">
        <div className="surface-title"><span>Authorization preview</span>{selected&&<DecisionBadge value="READY"/>}</div>
        {selected?<><div className="selected-product"><div className="product-monogram">{selected.brand.slice(0,2).toUpperCase()}</div><div><strong>{selected.product}</strong><span>{selected.variant} · {selected.sku}</span></div></div><div className="authority-ledger"><div><span>Agent proposes</span><b>{selected.sku} × {selected.quantity}</b></div><div><span>Merchant price</span><b>{formatMinorCurrency(selected.total_minor,selected.currency)}</b></div><div><span>Available inventory</span><b>{selected.inventory} units</b></div><div><span>Human maximum</span><b>{formatMinorCurrency(plan?.max_amount_minor??selected.total_minor)}</b></div><div><span>Price authority</span><b>MERCHANT CATALOG</b></div></div>{plan&&<div className="recommendation-note"><Sparkles size={15}/><span><b>Recommendation</b>{plan.recommendation_reason}</span></div>}{transaction?<div className="execution-result"><div><DecisionBadge value={transaction.decision}/><DecisionBadge value={transaction.payment_state}/></div><strong>{transaction.transaction_id}</strong><span>{transaction.reason_codes.length?transaction.reason_codes.join(' · '):'All deterministic authority checks passed.'}</span>{transaction.inventory_after!==null&&['AUTHORIZED','CAPTURED','RECOVERED'].includes(transaction.payment_state)&&<div className="inventory-commit"><PackageCheck size={15}/><span><b>Inventory committed</b>{transaction.quantity} unit{transaction.quantity===1?'':'s'} deducted · {transaction.inventory_after} remaining</span></div>}<Link href={`/transactions/${transaction.transaction_id}`}>Open transaction passport <ArrowRight size={14}/></Link>{transaction.payment_state==='FAILED'&&<Link href="/recovery">Open Recovery Center <RotateCcw size={14}/></Link>}</div>:<div className="buyer-actions"><button className="ops-primary" disabled={busy||selected.inventory<selected.quantity} onClick={authorize}><LockKeyhole size={15}/>{busy?'Evaluating authority…':'Authorize exact purchase'}</button>{payment?.mode==='LOCAL_TEST'&&<button className="ops-secondary" disabled={busy} onClick={failLocally}>Simulate failed payment</button>}</div>}</>:<div className="side-empty"><LockKeyhole size={22}/><span>Select a catalog match to preview the exact authority boundary.</span></div>}
      </aside>
    </div>
    {plan&&<div className="tool-trace"><span>Agent trace</span>{plan.tool_trace.map(tool=><code key={tool}>{tool}</code>)}</div>}
  </Shell>
}

const defaultAttack:AttackPayload={scenario:'Quantity Escalation',quantity:5,tamper_checkout:false,forged_signature:false,expire_authorization:false}

export function AttackLabConsole(){
  const [config,setConfig]=useState<AttackConfigApi|null>(null)
  const [payload,setPayload]=useState<AttackPayload>(defaultAttack)
  const [amount,setAmount]=useState('')
  const [result,setResult]=useState<AttackApi|null>(null)
  const [busy,setBusy]=useState(false)
  const [error,setError]=useState('')
  useEffect(()=>{intentLockApi.attackConfig().then(c=>{setConfig(c);setPayload(v=>({...v,sku:c.authority.sku,merchant_override:c.merchant_id}));setAmount(String(c.authority.max_amount_minor/100*5))}).catch(e=>setError(e instanceof Error?e.message:'Unable to load Attack Lab'))},[])
  const applyPreset=(name:string)=>{if(!config)return;const preset=config.presets.find(p=>p.name===name);let sku=config.authority.sku;let quantity=preset?.quantity??1;let merchant=config.merchant_id;let nextAmount=config.authority.max_amount_minor/100*quantity;if(name==='Wrong Product')sku=config.products.find(p=>p.brand!==config.authority.brand)?.sku??config.products.at(-1)?.sku??sku;if(name==='Wrong Merchant')merchant='merchant_untrusted_77';if(name==='Checkout Mutation')nextAmount+=2500;setPayload({scenario:name,sku,quantity,merchant_override:merchant,tamper_checkout:Boolean(preset?.tamper_checkout),forged_signature:Boolean(preset?.forged_signature),expire_authorization:Boolean(preset?.expire_authorization)});setAmount(String(nextAmount));setResult(null)}
  const run=async()=>{setBusy(true);setError('');try{setResult(await intentLockApi.runAttack({...payload,asserted_total_minor:Math.max(1,Math.round(Number(amount||0)*100))}))}catch(e){setError(e instanceof Error?e.message:'Attack execution failed')}finally{setBusy(false)}}
  const authority=config?.authority
  return <Shell title="Attack Lab" compact>
    <header className="operation-pagebar attack-pagebar"><div><span className="ops-eyebrow"><Zap size={14}/> ADVERSARIAL CONTROL VALIDATION</span><h1>Attack Lab</h1><p>Compare signed human authority with an editable agent payload, then inspect every kernel decision.</p></div><div className="operation-page-actions"><Link href="/dashboard">← Control room</Link><span className="lab-environment">LIVE KERNEL · PAYMENT HARD-GATED</span></div></header>
    {busy&&<div className="operation-progress danger-progress"><i/><span>Executing adversarial request through the production policy kernel…</span></div>}
    <div className="attack-layout">
      <aside className="ops-surface attack-presets"><div className="surface-title"><span>Attack presets</span><Zap size={15}/></div>{(config?.presets??[]).map(item=><button className={payload.scenario===item.name?'active':''} key={item.name} onClick={()=>applyPreset(item.name)}><strong>{item.name}</strong><small>{item.description}</small></button>)}</aside>
      <section className="attack-main">
        <div className="attack-comparison">
          <div className="ops-surface authority-column"><div className="surface-title"><span>Human authority</span><DecisionBadge value="SIGNED"/></div><div className="payload-fields readonly"><label>Product<input readOnly value={authority?.product??'Loading…'}/></label><label>SKU<input readOnly value={authority?.sku??''}/></label><label>Maximum quantity<input readOnly value={authority?.max_quantity??1}/></label><label>Maximum spend<input readOnly value={authority?formatMinorCurrency(authority.max_amount_minor):'—'}/></label><label className="wide">Authorized merchant<input readOnly value={config?.merchant_id??''}/></label></div></div>
          <div className="ops-surface malicious-column"><div className="surface-title"><span>Agent payload</span><DecisionBadge value="UNTRUSTED INPUT"/></div><div className="payload-fields"><label>Requested product<select value={payload.sku??''} onChange={e=>setPayload(v=>({...v,sku:e.target.value}))}>{(config?.products??[]).map(p=><option value={p.sku} key={p.sku}>{p.product} · {p.sku}</option>)}</select></label><label>Quantity<input type="number" min={1} max={25} value={payload.quantity??1} onChange={e=>setPayload(v=>({...v,quantity:Number(e.target.value)}))}/></label><label>Asserted total (₹)<input type="number" min={1} value={amount} onChange={e=>setAmount(e.target.value)}/></label><label>Payee merchant<input value={payload.merchant_override??''} onChange={e=>setPayload(v=>({...v,merchant_override:e.target.value}))}/></label></div><div className="tamper-toggles"><label><input type="checkbox" checked={Boolean(payload.tamper_checkout)} onChange={e=>setPayload(v=>({...v,tamper_checkout:e.target.checked}))}/> Tamper checkout hash</label><label><input type="checkbox" checked={Boolean(payload.forged_signature)} onChange={e=>setPayload(v=>({...v,forged_signature:e.target.checked}))}/> Forge agent signature</label><label><input type="checkbox" checked={Boolean(payload.expire_authorization)} onChange={e=>setPayload(v=>({...v,expire_authorization:e.target.checked}))}/> Expire mandate</label></div></div>
        </div>
        <button className="ops-primary run-attack" disabled={busy||!config} onClick={run}><Zap size={15}/>{busy?'Executing against live kernel…':'Run adversarial request'}</button>
        {error&&<div className="ops-alert danger"><AlertTriangle size={16}/>{error}</div>}
        <section className="ops-surface attack-result"><div className="surface-title"><span>Kernel evidence</span>{result?<DecisionBadge value={result.result}/>:<DecisionBadge value="READY"/>}</div>{result?.transaction?<><div className="attack-proof"><div><strong>{result.transaction.checks.filter(c=>c.result==='PASS').length}</strong><span>checks passed</span></div><div><strong>{result.transaction.checks.filter(c=>c.result==='FAIL').length}</strong><span>controls failed</span></div><div><strong>{result.transaction.razorpay_api_calls}</strong><span>Razorpay API calls</span></div><div><strong>{result.transaction.latency_ms}ms</strong><span>kernel latency</span></div></div><div className="check-matrix">{result.transaction.checks.map(check=><div className={check.result==='FAIL'?'failed':''} key={check.name}>{check.result==='FAIL'?<AlertTriangle size={14}/>:<Check size={14}/>}<span><b>{check.name}</b><small>{check.reason_code??check.detail}</small></span><em>{check.result}</em></div>)}</div>{result.tool_requests&&<div className="duplicate-proof"><ShieldCheck size={17}/><span><b>{result.tool_requests} requests → {result.economic_actions} economic action</b>{result.duplicates_prevented} duplicate payment attempts contained.</span></div>}</>:<div className="ops-empty compact"><ShieldCheck size={20}/><strong>No simulation run yet</strong><span>The result will be persisted as real transaction and audit evidence.</span></div>}</section>
      </section>
    </div>
  </Shell>
}

export function RecoveryConsole(){
  const [data,setData]=useState<RecoveryApi|null>(null)
  const [selectedCase,setSelectedCase]=useState('')
  const [candidateSku,setCandidateSku]=useState('')
  const [payment,setPayment]=useState<PaymentConfigApi|null>(null)
  const [transaction,setTransaction]=useState<TransactionApi|null>(null)
  const [busy,setBusy]=useState(false)
  const [error,setError]=useState('')
  const load=async()=>{try{const [cases,config]=await Promise.all([intentLockApi.recovery(),intentLockApi.paymentConfig()]);setData(cases);setPayment(config);const first=cases.items.find(c=>c.status==='OPEN')??cases.items[0];if(first){setSelectedCase(v=>v||first.case_id);setCandidateSku(v=>v||first.candidates.find(c=>c.eligible)?.sku||'')}}catch(e){setError(e instanceof Error?e.message:'Unable to load Recovery Center')}}
  useEffect(()=>{load()},[])
  const record=data?.items.find(c=>c.case_id===selectedCase)??data?.items[0]
  const candidates=record?.candidates??[]
  const candidate=candidates.find(c=>c.sku===candidateSku)??candidates.find(c=>c.eligible)
  const chooseCase=(id:string)=>{const next=data?.items.find(c=>c.case_id===id);setSelectedCase(id);setCandidateSku(next?.candidates.find(c=>c.eligible)?.sku??'');setTransaction(null)}
  const recover=async()=>{if(!record||!candidate)return;setBusy(true);setError('');try{let tx=await intentLockApi.executeRecovery(record.case_id,candidate.sku,1);if(tx.decision==='ALLOW'&&tx.payment_state==='ORDER_CREATED'&&payment)tx=await completePayment(tx,payment);setTransaction(tx);await load()}catch(e){setError(e instanceof Error?e.message:'Recovery attempt failed')}finally{setBusy(false)}}
  return <Shell title="Recovery Center" subtitle="Resolve verified payment failures while preserving the original signed authority.">
    <div className="recovery-summary"><div><span>Open cases</span><strong>{data?.open??0}</strong></div><div><span>Recovered</span><strong>{data?.recovered??0}</strong></div><div><span>Recovered GMV</span><strong>{formatMinorCurrency(data?.recovered_gmv_minor??0)}</strong></div><div><span>Payment rail</span><DecisionBadge value={payment?.mode??'LOADING'}/></div></div>
    {error&&<div className="ops-alert danger"><AlertTriangle size={16}/>{error}</div>}
    {(data?.items.length??0)>0?<div className="recovery-layout"><aside className="ops-surface case-list"><div className="surface-title"><span>Exception queue</span><RefreshCw size={14}/></div>{data?.items.map(item=><button className={record?.case_id===item.case_id?'active':''} onClick={()=>chooseCase(item.case_id)} key={item.case_id}><span><strong>{item.case_id}</strong><small>{item.product} · {formatMinorCurrency(item.amount_minor)}</small></span><DecisionBadge value={item.status}/></button>)}</aside><section className="ops-surface recovery-detail">{record&&<><div className="surface-title"><span>{record.case_id}</span><DecisionBadge value={record.status}/></div><div className="recovery-origin"><div><span>Failed transaction</span><Link href={`/transactions/${record.original_transaction_id}`}>{record.original_transaction_id}</Link></div><div><span>Original product</span><b>{record.product}</b></div><div><span>Original amount</span><b>{formatMinorCurrency(record.amount_minor)}</b></div><div><span>Attempts</span><b>{record.attempts}</b></div></div><div className="authority-banner"><LockKeyhole size={16}/><span><b>Authority carried forward</b>{record.authority.brand??'Any brand'} · {record.authority.category??'Any category'} · quantity ≤ {record.authority.max_quantity} · maximum {formatMinorCurrency(record.authority.max_amount_minor)}</span></div><div className="candidate-heading"><div><strong>Recovery candidates</strong><span>Eligibility is computed against the original mandate before execution.</span></div></div><div className="candidate-table">{candidates.map(item=><button disabled={!item.eligible||record.status!=='OPEN'} className={cx(candidate?.sku===item.sku&&'selected',!item.eligible&&'ineligible')} key={item.sku} onClick={()=>setCandidateSku(item.sku)}><span className="match-radio"/><span><strong>{item.product}</strong><small>{item.variant} · {item.sku}</small></span><span><b>{formatMinorCurrency(item.unit_price_minor,item.currency)}</b><small>{item.inventory} in stock</small></span><DecisionBadge value={item.eligible?'WITHIN AUTHORITY':'BLOCKED'}/></button>)}</div>{transaction&&<div className="execution-result"><div><DecisionBadge value={transaction.decision}/><DecisionBadge value={transaction.payment_state}/></div><strong>{transaction.transaction_id}</strong><Link href={`/transactions/${transaction.transaction_id}`}>Open recovery passport <ArrowRight size={14}/></Link></div>}{record.last_reason&&<div className="ops-alert"><FileCheck2 size={16}/>{record.last_reason}</div>}{record.status==='OPEN'&&<button className="ops-primary" onClick={recover} disabled={!candidate||busy}><RotateCcw size={15}/>{busy?'Re-evaluating authority…':'Execute selected recovery'}</button>}</>}</section></div>:<div className="ops-surface recovery-empty"><CheckCircle2 size={28}/><strong>No unresolved payment failures</strong><span>Create a controlled failed payment from Reference Buyer to demonstrate authority-preserving recovery.</span><Link className="ops-primary" href="/buyer-demo">Open Reference Buyer <ArrowRight size={15}/></Link></div>}
  </Shell>
}

export function PaymentSetupConsole(){
  const [config,setConfig]=useState<PaymentConfigApi|null>(null)
  const [error,setError]=useState('')
  const load=()=>intentLockApi.paymentConfig().then(setConfig).catch(e=>setError(e instanceof Error?e.message:'Unable to read payment configuration'))
  useEffect(()=>{load()},[])
  return <Shell title="Payment Setup" subtitle="Connect IntentLock to your own Razorpay Test Mode account without exposing payment secrets.">
    <div className="payment-setup-grid"><section className="ops-surface payment-status-card"><div className="surface-title"><span>Razorpay connection</span><DecisionBadge value={config?.credentials_state??'CHECKING'}/></div><div className="connection-hero"><div className={cx('connection-icon',config?.razorpay_enabled&&'connected')}><CreditCard/></div><div><strong>{config?.razorpay_enabled?'Razorpay Test Mode connected':'Local payment simulator active'}</strong><span>{config?.razorpay_enabled?'Allowed transactions create real Razorpay Test Orders and open Standard Checkout.':'Add your account-specific Test Mode keys to activate real Razorpay Checkout.'}</span></div></div><div className="connection-checks"><div><span>Execution mode</span><b>{config?.mode??'—'}</b></div><div><span>Checkout</span><b>{config?.checkout_ready?'READY':'LOCAL ONLY'}</b></div><div><span>Webhook</span><b>{config?.webhook_ready?'VERIFIED SECRET READY':'NOT CONFIGURED'}</b></div><div><span>Key ID</span><b>{config?.key_id_masked??'NOT CONFIGURED'}</b></div></div><button className="ops-secondary" onClick={load}><RefreshCw size={14}/>Refresh connection</button>{error&&<div className="ops-alert danger"><AlertTriangle size={16}/>{error}</div>}</section><section className="ops-surface setup-instructions"><div className="surface-title"><span>Activation checklist</span><ShieldCheck size={15}/></div><ol><li><span>1</span><div><strong>Generate your own Test Mode keys</strong><p>In Razorpay Dashboard, switch to Test Mode and open Account &amp; Settings → API Keys → Generate Key.</p></div></li><li><span>2</span><div><strong>Paste keys into backend/.env</strong><pre>RAZORPAY_KEY_ID=rzp_test_...{`\n`}RAZORPAY_KEY_SECRET=...{`\n`}RAZORPAY_WEBHOOK_SECRET=...</pre><p>The Key Secret is backend-only. Never paste it into frontend code or publish it.</p></div></li><li><span>3</span><div><strong>Restart FastAPI</strong><p>The status on this page changes to CONNECTED after the backend reloads the environment.</p></div></li><li><span>4</span><div><strong>Add the Test webhook when deployed</strong><p>Use <code>/api/v1/payments/webhook</code> and enable authorized, captured, failed, and order-paid events.</p></div></li></ol><div className="security-note"><LockKeyhole size={17}/><span><b>Why keys are not included</b>Razorpay credentials belong to your account. Public/shared credentials would be unsafe and cannot prove your integration to judges.</span></div></section></div>
  </Shell>
}
