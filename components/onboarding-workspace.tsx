'use client'

import { useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import {
  formatFreshness,
  formatMinorCurrency,
  intentLockApi,
  type CatalogResponse,
  type MerchantResponse,
  type ReadinessResponse,
} from '@/lib/intentlock-api'

type CheckState = 'pending' | 'current' | 'complete'

const steps = [
  ['Payment', 'Connect payment infrastructure'],
  ['Catalog', 'Enable product discovery'],
  ['Policy', 'Define autonomous authority'],
  ['Identity', 'Provision merchant trust'],
  ['Discovery', 'Enable agent access'],
  ['Readiness', 'Validate and activate'],
]

function Status({ children, tone = 'neutral' }: { children: React.ReactNode; tone?: 'neutral' | 'good' | 'accent' }) {
  return <span className={`setup-status ${tone}`}>{children}</span>
}

function StepRail({ current, merchantName }: { current: number; merchantName: string }) {
  return <aside className="setup-rail">
    <Link href="/" className="setup-brand"><span className="setup-mark">◎</span><span>intent<span>lock</span></span></Link>
    <span className="setup-kicker">MERCHANT SETUP</span>
    <nav className="setup-steps" aria-label="Onboarding progress">
      {steps.map(([title, description], index) => {
        const state: CheckState = index + 1 < current ? 'complete' : index + 1 === current ? 'current' : 'pending'
        return <div className={`setup-step ${state}`} key={title}><span className="setup-step-number">{state === 'complete' ? '✓' : String(index + 1).padStart(2, '0')}</span><span><b>{title}</b><small>{description}</small></span></div>
      })}
    </nav>
    <div className="setup-rail-bottom"><strong>{merchantName}</strong><small>Environment <b>TEST</b></small><Link href="/audit-log">Documentation ↗</Link><Link href="/audit-log">Need help? ↗</Link></div>
  </aside>
}

function PaymentStep({ connected, setConnected, onError }: { connected: boolean; setConnected: (value: boolean) => void; onError:(message:string)=>void }) {
  const testConnection = async () => {
    try { onError(''); await intentLockApi.markPaymentConnected(); setConnected(true) }
    catch (error) { onError(error instanceof Error ? error.message : 'Unable to test payment connection') }
  }
  return <div className="setup-columns"><section className="setup-main"><span className="setup-kicker">PAYMENT INFRASTRUCTURE</span><h2>Connect payment infrastructure</h2><p className="setup-lead">Connect your payment rail so IntentLock can evaluate agent requests before money moves.</p><div className="setup-form-grid"><label>Provider<input value="Razorpay" readOnly /></label><label>Environment<input value="Test Mode" readOnly /></label><label>Key ID<input placeholder="rzp_test_••••••••" /></label><label>Secret<input type="password" placeholder="••••••••••••" /></label></div><button className="primary-action" onClick={testConnection}>{connected ? 'Connection tested' : 'Test connection'} →</button><div className="capability-row"><span>Orders <b>READY</b></span><span>Payments <b>READY</b></span><span>Webhooks <b>READY</b></span></div></section><aside className="setup-context"><span className="setup-kicker">CONNECTION STATUS</span><h3>{connected ? 'CONNECTED' : 'READY TO CONNECT'}</h3>{[['Provider', 'Razorpay'], ['Environment', 'Test Mode'], ['Orders', connected ? 'CHECKED' : 'READY'], ['Payments', connected ? 'CHECKED' : 'READY'], ['Webhooks', connected ? 'CHECKED' : 'READY']].map(([label, value]) => <div className="context-row" key={label}><span>{label}</span><b>{value}</b></div>)}{connected && <div className="success-note">✓ Test Mode rail configured for local development</div>}</aside></div>
}

function CatalogStep({ imported, setImported, onCatalogChanged, onError }: { imported: boolean; setImported: (value: boolean) => void; onCatalogChanged:(response:CatalogResponse)=>void; onError:(message:string)=>void }) {
  const csvRef=useRef<HTMLInputElement>(null), jsonRef=useRef<HTMLInputElement>(null)
  const [catalogState,setCatalogState]=useState<CatalogResponse|null>(null)
  const [loading,setLoading]=useState(true)

  useEffect(()=>{
    let active=true
    intentLockApi.agentCatalog().then(r=>{
      if(!active)return
      setCatalogState(r)
      setImported(r.summary.skus>0)
      onCatalogChanged(r)
    }).catch(()=>{}).finally(()=>{if(active)setLoading(false)})
    return()=>{active=false}
  },[])

  const apply=(r:CatalogResponse)=>{setCatalogState(r);setImported(r.summary.skus>0);onCatalogChanged(r)}
  const useDemo=async()=>{try{onError('');setLoading(true);apply(await intentLockApi.useDemoCatalog())}catch(error){onError(error instanceof Error?error.message:'Unable to load demo catalog')}finally{setLoading(false)}}
  const upload=async(file?:File)=>{if(!file)return;try{onError('');setLoading(true);apply(await intentLockApi.uploadCatalog(file))}catch(error){onError(error instanceof Error?error.message:'Unable to upload catalog')}finally{setLoading(false)}}
  const summary=catalogState?.summary??{merchant_id:'',products:0,skus:0,brands:0,categories:0,visible_skus:0,last_updated_at:null}
  const rows=(catalogState?.items??[]).slice(0,3)

  return <div className="setup-columns"><section className="setup-main"><span className="setup-kicker">AGENT-READABLE COMMERCE</span><h2>Make your products discoverable to AI agents</h2><p className="setup-lead">IntentLock gives autonomous agents an authoritative catalog to discover, evaluate, and transact against.</p><div className="catalog-options"><button className={imported ? 'selected' : ''} onClick={useDemo} disabled={loading}><b>Use Demo Catalog</b><small>24 products · recommended</small></button><button onClick={()=>csvRef.current?.click()} disabled={loading}><b>Upload CSV</b><small>Import a product feed</small></button><button onClick={()=>jsonRef.current?.click()} disabled={loading}><b>Upload JSON</b><small>Use agent metadata</small></button><input ref={csvRef} hidden type="file" accept=".csv,text/csv" onChange={e=>upload(e.target.files?.[0])}/><input ref={jsonRef} hidden type="file" accept=".json,application/json" onChange={e=>upload(e.target.files?.[0])}/></div>{imported && <table className="compact-table"><thead><tr><th>SKU</th><th>Product</th><th>Price</th><th>Inventory</th><th>Visible</th></tr></thead><tbody>{rows.map(row => <tr key={row.sku}><td>{row.sku}</td><td>{row.product}</td><td>{formatMinorCurrency(row.price_minor,row.currency)}</td><td>{row.inventory}</td><td><Status tone={row.visible?'good':'neutral'}>{row.visible?'YES':'NO'}</Status></td></tr>)}</tbody></table>}</section><aside className="setup-context"><span className="setup-kicker">CATALOG STATUS</span><h3>{loading?'Loading…':`${summary.products} Products`}</h3><div className="catalog-counts"><b>{summary.skus}<small>SKUs</small></b><b>{summary.brands}<small>Brands</small></b><b>{summary.categories}<small>Categories</small></b></div><span className="setup-kicker validation-label">VALIDATION</span>{['Required fields','SKU uniqueness','Pricing','Inventory','Agent metadata'].map(label=><div className="context-row" key={label}><span>{label}</span><Status tone={imported?'good':'neutral'}>{imported?'PASS':'PENDING'}</Status></div>)}<div className="context-footer">Catalog freshness <b>{formatFreshness(summary.last_updated_at)}</b></div></aside></div>
}

function PolicyStep({published}:{published:boolean}) { return <div className="setup-columns"><section className="setup-main"><span className="setup-kicker">MERCHANT POLICY</span><h2>Define the merchant money boundary</h2><p className="setup-lead">Set the authority IntentLock will enforce across every autonomous economic action.</p><div className="policy-grid"><div><span className="setup-kicker">MONEY</span><label>Maximum autonomous transaction<input value="₹50,000" readOnly /></label><label>Step-Up above<input value="₹25,000" readOnly /></label><label>Daily AI spend<input value="₹1,00,000" readOnly /></label></div><div><span className="setup-kicker">COMMERCE</span><label>Maximum discount<input value="5%" readOnly /></label><label>Alternative SKU<input value="Allowed" readOnly /></label><label>Merchant switching<input value="Blocked" readOnly /></label><span className="setup-kicker policy-sub">RECOVERY</span><label>Maximum attempts<input value="2" readOnly /></label><label>Unknown agent<input value="STEP-UP" readOnly /></label></div></div></section><aside className="setup-context authority-card"><span className="setup-kicker">EFFECTIVE AUTHORITY</span><div className="authority-equation"><b>Human Authorization</b><span>∩</span><b>Merchant Policy</b><span>=</span><strong>Actual Economic Authority</strong></div><div className="context-row"><span>Human Limit</span><b>₹20,000</b></div><div className="context-row"><span>Merchant Limit</span><b>₹50,000</b></div><div className="context-row"><span>Effective Limit</span><b>₹20,000</b></div><div className="context-row"><span>Policy Version</span><b>{published?'v1 · PUBLISHED':'v1 · DRAFT'}</b></div></aside></div> }

function IdentityStep({merchant}:{merchant:MerchantResponse|null}) {
  const active=merchant?.identity_active??false
  const provisioning=[['Merchant identifier','COMPLETE'],['Signing key',active?'COMPLETE':'PENDING'],['Public key',active?'REGISTERED':'PENDING'],['Policy binding',active?'COMPLETE':'PENDING'],['Trust endpoint',active?'READY':'PENDING']]
  return <div className="setup-columns"><section className="setup-main"><span className="setup-kicker">TRUST PROVISIONING</span><h2>Provision merchant trust identity</h2><p className="setup-lead">Create the signed identity that binds your merchant, policy, and agents together.</p><div className="provision-list">{provisioning.map(([label,status]) => <div key={label}><span className="provision-check">{status==='PENDING'?'•':'✓'}</span><b>{label}</b><Status tone={status==='PENDING'?'neutral':'good'}>{status}</Status></div>)}</div></section><aside className="setup-context"><span className="setup-kicker">MERCHANT IDENTITY</span><h3>{merchant?.merchant_name??'Your Store'}</h3>{[['Merchant ID',merchant?.merchant_id??'—'],['Algorithm',merchant?.identity_algorithm??'Pending'],['Key Fingerprint',merchant?.identity_fingerprint??'Not provisioned'],['Policy',merchant?.policy_version==='none'?'Not published':merchant?.policy_version??'—'],['Status',active?'ACTIVE':'PENDING']].map(([label,value]) => <div className="context-row" key={label}><span>{label}</span><b>{value}</b></div>)}</aside></div>
}

function DiscoveryStep({ tested, setTested, merchantName }: { tested: boolean; setTested: (value: boolean) => void; merchantName:string }) {
  const [running,setRunning]=useState(false)
  const [discovery,setDiscovery]=useState<Awaited<ReturnType<typeof intentLockApi.agentDiscovery>>|null>(null)
  const [apiError,setApiError]=useState('')

  const load=async()=>{try{const d=await intentLockApi.agentDiscovery();setDiscovery(d);setTested(d.status==='AI_TRANSACTABLE')}catch(error){setApiError(error instanceof Error?error.message:'Unable to load discovery state')}}
  useEffect(()=>{load()},[])
  const runTest=async()=>{
    setRunning(true);setApiError('')
    try{
      const test=await intentLockApi.testAgentDiscovery()
      const d=await intentLockApi.agentDiscovery()
      setDiscovery(d)
      setTested(test.result==='DISCOVERABLE')
      if(test.result!=='DISCOVERABLE')setApiError('Discovery prerequisites are not ready yet.')
    }catch(error){setApiError(error instanceof Error?error.message:'Unable to run discovery test')}
    finally{setRunning(false)}
  }
  return <div className="setup-columns"><section className="setup-main"><span className="setup-kicker">AGENT DISCOVERY</span><h2>Enable agent discovery</h2><p className="setup-lead">Allow autonomous commerce agents to discover your merchant, catalog, and transaction capabilities.</p><div className="endpoint-card"><span className="setup-kicker">AGENT COMMERCE ENDPOINT</span>{[['Merchant',merchantName],['Discovery',tested?'ENABLED':'PENDING'],['Catalog Endpoint',discovery?.catalog_endpoint??'Provisioning…'],['Policy Endpoint',discovery?.policy_endpoint??'Provisioning…'],['Checkout Endpoint',discovery?.checkout_endpoint??'Provisioning…']].map(([label,value]) => <div className="context-row" key={label}><span>{label}</span><b>{value}</b></div>)}</div><div className="protocol-row"><span>REST <b>{discovery?.protocols.rest??'ACTIVE'}</b></span><span>ACP <b>{discovery?.protocols.acp??'PLANNED'}</b></span><span>UCP <b>{discovery?.protocols.ucp??'PLANNED'}</b></span></div></section><aside className="setup-context"><span className="setup-kicker">DISCOVERY TEST</span><h3>{tested ? 'DISCOVERABLE' : 'NOT TESTED'}</h3>{tested && discovery ? <><div className="discovery-counts"><b>{discovery.products}<small>Products available</small></b><b>{discovery.skus}<small>SKUs</small></b><b>{discovery.categories}<small>Categories</small></b></div><div className="success-note">✓ Real API resolved merchant, catalog, policy, checkout, and transaction capability</div></> : <><p className="context-copy">Run the real FastAPI discovery preflight before opening agent traffic.</p><button className="secondary-action" onClick={runTest} disabled={running}>{running?'Testing backend…':'Run discovery test →'}</button>{apiError&&<div className="success-note">{apiError}</div>}</>}</aside></div>
}

function ReadinessStep({merchant,readiness}:{merchant:MerchantResponse|null;readiness:ReadinessResponse|null}) {
  const labels:Record<string,string>={payment_infrastructure:'Payment Infrastructure',agent_catalog:'Agent Catalog',merchant_policy:'Merchant Policy',merchant_identity:'Merchant Identity',agent_discovery:'Agent Discovery',intentlock_gateway:'IntentLock Gateway'}
  const fallback=[['payment_infrastructure','CHECKING'],['agent_catalog','CHECKING'],['merchant_policy','CHECKING'],['merchant_identity','CHECKING'],['agent_discovery','CHECKING'],['intentlock_gateway','CHECKING']]
  const checks=readiness?.checks.map(c=>[c.name,c.status])??fallback
  const ready=readiness?.overall==='AI_TRANSACTABLE'
  return <div className="readiness-layout"><section className="setup-main"><span className="setup-kicker">READINESS CHECKLIST</span><h2>{ready?'Ready for agentic commerce':'Complete setup to activate'}</h2><p className="setup-lead">{ready?`${merchant?.merchant_name??'Your store'} can now be discovered by AI agents and transact safely through IntentLock.`:'IntentLock is validating the real backend state for each required onboarding step.'}</p><div className="readiness-list">{checks.map(([name,status]) => {const pass=status!=='NOT_READY'&&status!=='CHECKING';return <div key={name}><span>{pass?'✓':'•'}</span><b>{labels[name]??name}</b><Status tone={pass?'good':'neutral'}>{status}</Status></div>})}</div></section><aside className="setup-context"><span className="setup-kicker">MERCHANT SUMMARY</span><h3>{merchant?.merchant_name??'Your Store'}</h3><p className="mono">{merchant?.merchant_id??'—'}</p>{[['Catalog',merchant?`${merchant.catalog.products} products · ${merchant.catalog.skus} SKUs`:'Checking…'],['Policy',merchant?.policy_version==='none'?'Not published':merchant?.policy_version??'Checking…'],['Identity',merchant?.identity_fingerprint??'Checking…'],['Environment',merchant?.environment??'Razorpay Test Mode'],['Readiness',readiness?.overall??'CHECKING']].map(([label,value]) => <div className="context-row" key={label}><span>{label}</span><b>{value}</b></div>)}</aside><div className="architecture"><span>AI Agent</span><i>→</i><span>Discover Merchant</span><i>→</i><span>Catalog</span><i>→</i><span>IntentLock</span><i>→</i><span>Razorpay Test Mode</span><strong>{ready?'AI-TRANSACTABLE':'NOT READY'}</strong></div></div>
}

export function OnboardingWorkspace() {
  const [step, setStep] = useState(1)
  const [connected, setConnected] = useState(false)
  const [imported, setImported] = useState(false)
  const [tested, setTested] = useState(false)
  const [policyPublished,setPolicyPublished]=useState(false)
  const [readiness,setReadiness]=useState<ReadinessResponse|null>(null)
  const [merchant,setMerchant]=useState<MerchantResponse|null>(null)
  const [flowError,setFlowError]=useState('')
  const router = useRouter()
  const [busy, setBusy] = useState(false)

  const applyReadiness=(r:ReadinessResponse)=>{
    setReadiness(r)
    const byName=Object.fromEntries(r.checks.map(c=>[c.name,c.status]))
    setConnected(byName.payment_infrastructure==='CONNECTED')
    setImported(byName.agent_catalog==='VALIDATED')
    setPolicyPublished(byName.merchant_policy==='PUBLISHED')
    setTested(byName.agent_discovery==='ENABLED')
  }

  const refreshState=async()=>{
    const [r,m]=await Promise.all([intentLockApi.readiness(),intentLockApi.merchant()])
    applyReadiness(r);setMerchant(m)
    return {readiness:r,merchant:m}
  }

  useEffect(()=>{
    let active=true
    Promise.all([intentLockApi.me(),intentLockApi.readiness(),intentLockApi.merchant()]).then(([me,r,m])=>{
      if(!active)return
      applyReadiness(r);setMerchant(m)
      if(me.merchant.onboarding_completed) router.replace('/dashboard')
    }).catch(error=>{if(active)setFlowError(error instanceof Error?error.message:'Unable to load onboarding state')})
    return()=>{active=false}
  },[router])

  const current = steps[step - 1]
  const requirementMessage = step===1&&!connected ? 'Test the payment connection before continuing.' : step===2&&!imported ? 'Choose Demo Catalog or upload a CSV/JSON catalog before continuing.' : step===5&&!tested ? 'Run the discovery test successfully before continuing.' : ''

  const continueStep = async () => {
    setFlowError('')
    if(requirementMessage){setFlowError(requirementMessage);return}
    setBusy(true)
    try {
      if (step === 3) { await intentLockApi.publishDefaultPolicy(); setPolicyPublished(true) }
      if (step === 4) await intentLockApi.provisionIdentity()
      await refreshState()
      setStep(value => Math.min(6, value + 1))
    } catch(error) {
      setFlowError(error instanceof Error?error.message:'Unable to save this onboarding step')
    } finally { setBusy(false) }
  }

  const finish = async () => {
    setFlowError(''); setBusy(true)
    try {
      const {readiness:r}=await refreshState()
      if(r.overall!=='AI_TRANSACTABLE'){
        const missing=r.checks.filter(c=>c.status==='NOT_READY').map(c=>c.name.replaceAll('_',' ')).join(', ')
        setFlowError(`Complete the required setup first${missing?`: ${missing}`:''}.`)
        return
      }
      await intentLockApi.completeOnboarding()
      router.replace('/dashboard')
    } catch(error) {
      setFlowError(error instanceof Error?error.message:'Unable to activate the Merchant Console')
    } finally { setBusy(false) }
  }

  const onCatalogChanged=(response:CatalogResponse)=>{
    setImported(response.summary.skus>0)
    setMerchant(currentMerchant=>currentMerchant?{...currentMerchant,catalog:response.summary}:currentMerchant)
  }
  const back = () => { setFlowError(''); setStep(value => Math.max(1, value - 1)) }
  const readyToEnter=readiness?.overall==='AI_TRANSACTABLE'
  const merchantName=merchant?.merchant_name??'Your Store'

  return <main className="setup-app"><StepRail current={step} merchantName={merchantName}/><section className="setup-workspace"><header className="setup-header"><div><span className="setup-kicker">STEP {String(step).padStart(2, '0')} OF 06</span><strong>{current[0]}</strong></div><span className="setup-header-status">Razorpay Test Mode · {merchantName}</span></header><div className="setup-body">{step === 1 && <PaymentStep connected={connected} setConnected={setConnected} onError={setFlowError}/>} {step === 2 && <CatalogStep imported={imported} setImported={setImported} onCatalogChanged={onCatalogChanged} onError={setFlowError}/>} {step === 3 && <PolicyStep published={policyPublished}/>} {step === 4 && <IdentityStep merchant={merchant}/>} {step === 5 && <DiscoveryStep tested={tested} setTested={setTested} merchantName={merchantName}/>} {step === 6 && <ReadinessStep merchant={merchant} readiness={readiness}/>}</div><footer className="setup-actions"><button className="secondary-action" onClick={back} disabled={step === 1}>← Back</button><span className={flowError?'setup-action-error':''}>{flowError || (requirementMessage || `Step ${step} of 6 · ${current[0]}`)}</span>{step < 6 ? <button className="primary-action" onClick={continueStep} disabled={busy}>{busy?'Saving…':'Continue →'}</button> : <div className="final-actions"><Link className="secondary-action" href="/buyer-demo">Run Buyer Demo</Link><button className="primary-action" onClick={finish} disabled={busy||!readyToEnter} title={!readyToEnter?'Complete all readiness checks first':undefined}>{busy?'Activating…':'Enter Merchant Console →'}</button></div>}</footer></section></main>
}
