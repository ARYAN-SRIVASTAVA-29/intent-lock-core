const API_BASE_URL = process.env.NEXT_PUBLIC_INTENTLOCK_API_URL ?? 'http://localhost:8000/api/v1'

export class IntentLockApiError extends Error {
  status: number
  constructor(status: number, message: string) { super(message); this.status = status }
}

export type MerchantSession = { merchant_id:string; merchant_name:string; status:string; onboarding_completed:boolean; environment:string; discovery_enabled:boolean }
export type AuthMeResponse = { user_id:string; email:string; merchant:MerchantSession }
export type HealthResponse = { status:string; service:string; environment:string; timestamp:string }
export type CatalogProduct = { sku:string; product:string; brand:string; category:string; price_minor:number; currency:string; inventory:number; variant:string; delivery_days:number; visible:boolean; updated_at:string }
export type CatalogSummary = { merchant_id:string; products:number; skus:number; brands:number; categories:number; visible_skus:number; last_updated_at:string|null }
export type CatalogResponse = { summary:CatalogSummary; items:CatalogProduct[] }
export type DiscoveryResponse = { merchant_id:string; merchant_name:string; status:string; environment:string; catalog_endpoint:string; policy_endpoint:string; checkout_endpoint:string; transaction_endpoint:string; discovery_endpoint:string; products:number; skus:number; brands:number; categories:number; policy_version:string; protocols:{rest:string;acp:string;ucp:string;mcp:string;x402:string} }
export type DiscoveryTestResponse = { result:string; merchant_id:string; checks:Array<{step:string;status:string}> }
export type IdentityResponse = { merchant_id:string; merchant_name:string; algorithm:string; fingerprint:string; status:string }
export type ReadinessResponse = { merchant_id:string; overall:string; checks:Array<{name:string;status:string}> }
export type MerchantResponse = {
  merchant_id:string
  merchant_name:string
  environment:string
  status:string
  onboarding_completed:boolean
  payment_test_connected:boolean
  discovery_enabled:boolean
  identity_active:boolean
  identity_algorithm:string|null
  identity_fingerprint:string|null
  policy_version:string
  policy_status:string
  catalog:CatalogSummary
}
export type PolicyResponse = {
  merchant_id:string
  version:string
  status:string
  max_transaction_minor:number
  step_up_above_minor:number
  daily_spend_minor:number
  max_discount_pct:number
  max_recovery_attempts:number
  alternative_skus_allowed:boolean
  merchant_switching_allowed:boolean
  unknown_agent_action:string
}
export type PolicyUpdate = Omit<PolicyResponse,'merchant_id'|'version'|'status'>
export type CheckoutProposal = { checkout_id:string; merchant_id:string; merchant_name:string; sku:string; product:string; brand:string; category:string; variant:string; quantity:number; unit_price_minor:number; total_minor:number; currency:string; inventory_available:number; price_authority:string; checkout_hash:string; status:string }

async function request<T>(path:string, init:RequestInit = {}):Promise<T>{
  const isForm = typeof FormData !== 'undefined' && init.body instanceof FormData
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    credentials:'include',
    headers: isForm ? init.headers : {'Content-Type':'application/json', ...init.headers},
  })
  if(!response.ok){
    let message=`IntentLock API ${response.status}`
    try { const body=await response.json(); message=body.detail ?? message } catch { message=await response.text() || message }
    throw new IntentLockApiError(response.status,message)
  }
  return response.json() as Promise<T>
}

export const intentLockApi = {
  health:()=>request<HealthResponse>('/health'),
  register:(store_name:string,email:string,password:string)=>request<AuthMeResponse>('/auth/register',{method:'POST',body:JSON.stringify({store_name,email,password})}),
  login:(email:string,password:string)=>request<AuthMeResponse>('/auth/login',{method:'POST',body:JSON.stringify({email,password})}),
  logout:()=>request<{ok:boolean}>('/auth/logout',{method:'POST'}),
  me:()=>request<AuthMeResponse>('/auth/me'),
  merchant:()=>request<MerchantResponse>('/merchant'),
  catalogProducts:(search?:string)=>request<CatalogResponse>(`/catalog/products${search?`?search=${encodeURIComponent(search)}`:''}`),
  useDemoCatalog:()=>request<CatalogResponse>('/catalog/demo',{method:'POST'}),
  uploadCatalog:(file:File)=>{const form=new FormData();form.append('file',file);return request<CatalogResponse>('/catalog/upload',{method:'POST',body:form})},
  agentCatalog:()=>request<CatalogResponse>('/agent-commerce/catalog'),
  agentDiscovery:()=>request<DiscoveryResponse>('/agent-commerce/discovery'),
  testAgentDiscovery:()=>request<DiscoveryTestResponse>('/agent-commerce/discovery/test',{method:'POST'}),
  checkoutProposal:(sku:string,quantity:number)=>request<CheckoutProposal>('/agent-commerce/checkouts',{method:'POST',body:JSON.stringify({sku,quantity})}),
  markPaymentConnected:()=>request<any>('/onboarding/payment/test',{method:'POST'}),
  publishDefaultPolicy:()=>request<PolicyResponse>('/onboarding/policy/publish',{method:'POST'}),
  currentPolicy:()=>request<PolicyResponse>('/policies/current'),
  updatePolicy:(payload:PolicyUpdate)=>request<PolicyResponse>('/policies/current',{method:'PUT',body:JSON.stringify(payload)}),
  provisionIdentity:()=>request<IdentityResponse>('/onboarding/identity/provision',{method:'POST'}),
  readiness:()=>request<ReadinessResponse>('/onboarding/readiness'),
  completeOnboarding:()=>request<any>('/onboarding/complete',{method:'POST'}),
  dashboard:()=>request<DashboardApi>('/dashboard'),
  transactions:()=>request<TransactionApi[]>('/transactions'),
  transaction:(id:string)=>request<TransactionApi>(`/transactions/${encodeURIComponent(id)}`),
  runDemoTransaction:(payload:{sku?:string;quantity?:number;max_quantity?:number;max_amount_minor?:number;natural_language?:string;payment_outcome?:'CAPTURED'|'FAILED'|'AUTHORIZED'})=>request<TransactionApi>('/transactions/demo',{method:'POST',body:JSON.stringify(payload)}),
  simulatePayment:(id:string,outcome:'CAPTURED'|'FAILED'|'AUTHORIZED')=>request<TransactionApi>(`/transactions/${encodeURIComponent(id)}/payments/simulate`,{method:'POST',body:JSON.stringify({outcome})}),
  approveStepUp:(id:string)=>request<TransactionApi>(`/transactions/${encodeURIComponent(id)}/step-up/approve`,{method:'POST'}),
  agents:()=>request<AgentsApi>('/agents'),
  recovery:()=>request<RecoveryApi>('/recovery'),
  executeRecovery:(caseId:string,sku:string,quantity=1)=>request<TransactionApi>(`/recovery/${encodeURIComponent(caseId)}/execute`,{method:'POST',body:JSON.stringify({sku,quantity})}),
  audit:()=>request<AuditApi>('/audit'),
  verifyAudit:()=>request<{verified:boolean;count:number;failed_sequence:number|null}>('/audit/verify',{method:'POST'}),
  attackConfig:()=>request<AttackConfigApi>('/attack-lab/config'),
  runAttack:(payload:string|AttackPayload)=>request<AttackApi>('/attack-lab/run',{method:'POST',body:JSON.stringify(typeof payload==='string'?{scenario:payload}:payload)}),
  buyerPlan:(userRequest:string)=>request<BuyerPlanApi>('/buyer-agent/plan',{method:'POST',body:JSON.stringify({request:userRequest})}),
  paymentConfig:()=>request<PaymentConfigApi>('/payments/config'),
  verifyPayment:(payload:{razorpay_order_id:string;razorpay_payment_id:string;razorpay_signature:string})=>request<TransactionApi>('/payments/verify',{method:'POST',body:JSON.stringify(payload)}),
}

export function formatMinorCurrency(amountMinor:number,currency='INR'){
  return new Intl.NumberFormat('en-IN',{style:'currency',currency,maximumFractionDigits:0}).format(amountMinor/100)
}

export function formatFreshness(timestamp:string|null){
  if(!timestamp)return 'Not synced'
  const ms=Date.now()-new Date(timestamp).getTime()
  if(ms<60_000)return 'just now'
  const minutes=Math.max(1,Math.floor(ms/60_000))
  if(minutes<60)return `${minutes}m ago`
  const hours=Math.floor(minutes/60)
  if(hours<24)return `${hours}h ago`
  return `${Math.floor(hours/24)}d ago`
}

export type IntentLockCheck = { name:string; result:string; reason_code:string|null; detail:string }
export type TransactionApi = {
  transaction_id:string; intent_id:string; mandate_id:string; agent_id:string; checkout_id:string;
  sku:string; product:string; quantity:number; amount_minor:number; currency:string; decision:string;
  payment_state:string; reason_codes:string[]; latency_ms:number; razorpay_api_calls:number;
  duplicate_count:number; recovery_of_transaction_id:string|null; created_at:string;
  intent_text:string; intent_brand:string|null; intent_category:string|null; intent_max_amount_minor:number; intent_max_quantity:number;
  mandate_status:string; mandate_payload_hash:string; mandate_expires_at:string|null; checkout_hash:string; unit_price_minor:number; price_authority:string;
  payment_order_id:string|null; payment_mode:string|null; payment_id:string|null; payment_signature_verified:boolean|null; checks:IntentLockCheck[]
  inventory_after:number|null;
}
export type DashboardApi = {
  merchant:{merchant_id:string;merchant_name:string;environment:string;discovery_enabled:boolean;identity_active:boolean;catalog:CatalogSummary}
  commerce:{captured_gmv_minor:number;economic_actions:number;discoverable_skus:number;registered_agents:number;recovered_gmv_minor:number}
  enforcement:{allowed:number;blocked:number;step_up:number;recovered:number;unsafe_gmv_minor:number;blocked_before_razorpay:number;duplicates_prevented:number;replays_rejected:number;critical_failures:number}
  transactions:Array<{transaction_id:string;agent_id:string;intent_id:string;mandate_id:string;product:string;sku:string;quantity:number;amount_minor:number;decision:string;payment_state:string;latency_ms:number;duplicate_count:number;created_at:string}>
  live_events:Array<{event_type:string;actor:string;transaction_id:string|null;created_at:string;event_hash:string}>
  agents:{registered:number;verified:number;step_up:number;suspended:number;items:Array<{agent_id:string;provider:string;trust:string;status:string;violations:number;last_seen_at:string|null}>}
  payments:{open_recovery_cases:number;recovered_cases:number;captured_gmv_minor:number;recovered_gmv_minor:number;webhook_state:string;mode:string}
  audit:{integrity:string;events:number;failed_sequence:number|null}
  operations:{
    inventory:{total_units:number;inventory_value_minor:number;sellable_skus:number;low_stock_skus:number;out_of_stock_skus:number;committed_units:number;items:Array<{sku:string;product:string;inventory:number;status:string}>}
    funnel:{evaluated:number;allowed:number;orders_created:number;authorized:number;captured:number;failed:number;allow_rate:number;payment_completion_rate:number}
    performance:{average_latency_ms:number;p95_latency_ms:number;actions_24h:number;critical_failures:number}
    activity_7d:Array<{date:string;label:string;total:number;allowed:number;blocked:number;step_up:number;captured_gmv_minor:number}>
    top_products:Array<{product:string;sku:string;actions:number;committed_units:number;captured_gmv_minor:number}>
  }
}
export type AgentsApi = {items:Array<{agent_id:string;provider:string;trust:string;status:string;algorithm:string;violations:number;last_seen_at:string|null;fingerprint:string}>;registered:number;verified:number;step_up:number;suspended:number}
export type RecoveryCandidateApi={sku:string;product:string;brand:string;category:string;variant:string;unit_price_minor:number;currency:string;inventory:number;delivery_days:number;eligible:boolean;reason_codes:string[]}
export type RecoveryApi = {items:Array<{case_id:string;original_transaction_id:string;status:string;attempts:number;recovered_transaction_id:string|null;last_reason:string|null;product:string;sku:string;amount_minor:number;created_at:string;authority:{brand:string|null;category:string|null;max_quantity:number;max_amount_minor:number;allowed_variants:string[]};candidates:RecoveryCandidateApi[]}>;open:number;recovered:number;recovered_gmv_minor:number}
export type AuditApi = {integrity:string;count:number;failed_sequence:number|null;items:Array<{sequence:number;event_type:string;actor:string;transaction_id:string|null;payload:Record<string,unknown>;previous_hash:string;event_hash:string;created_at:string}>}
export type AttackPayload={scenario:string;sku?:string;quantity?:number;asserted_total_minor?:number;merchant_override?:string;tamper_checkout?:boolean;forged_signature?:boolean;expire_authorization?:boolean}
export type AttackConfigApi={merchant_id:string;authority:{sku:string;product:string;brand:string;category:string;max_quantity:number;max_amount_minor:number;currency:string};products:Array<{sku:string;product:string;brand:string;category:string;unit_price_minor:number;currency:string;inventory:number}>;presets:Array<{name:string;description:string;quantity?:number;tamper_checkout?:boolean;forged_signature?:boolean;expire_authorization?:boolean}>}
export type AttackApi = {scenario:string;result:string;transaction?:TransactionApi;razorpay_api_calls?:number;tool_requests?:number;economic_actions?:number;duplicates_prevented?:number;razorpay_orders?:number;payment_orders?:number;first_transaction_id?:string;original_transaction_id?:string;authority?:{sku:string;product:string;max_quantity:number;max_amount_minor:number;merchant_id:string};submitted_payload?:{sku:string;product:string;quantity:number;asserted_total_minor:number;merchant_id:string;checkout_tampered:boolean;signature_forged:boolean;authorization_expired:boolean}}


export type BuyerMatchApi={sku:string;product:string;brand:string;category:string;variant:string;quantity:number;unit_price_minor:number;total_minor:number;currency:string;inventory:number;delivery_days:number;fit_score:number;recommendation_label:string}
export type BuyerPlanApi={agent_id:string;planning_mode:string;request:string;sku:string;product:string;brand:string;category:string;variant:string;quantity:number;unit_price_minor:number;max_amount_minor:number;currency:string;tool_trace:string[];explanation:string;matches:BuyerMatchApi[];recommended_sku:string;recommendation_reason:string}
export type PaymentConfigApi={razorpay_enabled:boolean;key_id:string|null;key_id_masked:string|null;mode:string;credentials_state:string;webhook_ready:boolean;checkout_ready:boolean}
