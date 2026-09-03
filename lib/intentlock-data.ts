export type Decision = 'ALLOW' | 'BLOCKED' | 'STEP-UP'
export type PaymentState = 'NOT_SENT' | 'CAPTURED' | 'FAILED' | 'RECOVERED'
export type Transaction = { id: string; intent: string; mandate: string; agent: string; product: string; sku: string; amount: string; decision: Decision; payment: PaymentState; created: string; reason?: string }

export const merchant = { name: 'Demo Audio Store', id: 'merchant_demo_001', policy: 'v1', environment: 'Razorpay Test Mode' }
export const authority = { request: 'Buy one pair of Sony noise-cancelling headphones under ₹20,000. Black preferred, blue is acceptable. Deliver before Monday.', intent: 'INT-001', mandate: 'MAN-001', brand: 'Sony', category: 'ANC Headphones', maxQuantity: '1', maxAmount: '₹20,000', colours: 'Black / Blue' }
export const catalog = [
 { sku:'SONY-XM5-BLK', product:'Sony WH-1000XM5', brand:'Sony', category:'ANC Headphones', price:'₹18,999', inventory:17, variant:'Black', delivery:'2 days', visible:true },
 { sku:'SONY-XM5-BLU', product:'Sony WH-1000XM5', brand:'Sony', category:'ANC Headphones', price:'₹18,999', inventory:8, variant:'Blue', delivery:'2 days', visible:true },
 { sku:'SONY-XM4-BLU', product:'Sony WH-1000XM4', brand:'Sony', category:'ANC Headphones', price:'₹16,999', inventory:11, variant:'Blue', delivery:'3 days', visible:true },
 { sku:'BOSE-QC-BLK', product:'Bose QuietComfort', brand:'Bose', category:'ANC Headphones', price:'₹23,999', inventory:14, variant:'Black', delivery:'2 days', visible:true },
 { sku:'AIRPODS-MAX', product:'AirPods Max', brand:'Apple', category:'ANC Headphones', price:'₹32,999', inventory:6, variant:'Space Gray', delivery:'3 days', visible:true },
 { sku:'SONY-WF1000-BLK', product:'Sony WF-1000XM5', brand:'Sony', category:'Earbuds', price:'₹21,990', inventory:24, variant:'Black', delivery:'2 days', visible:true },
 { sku:'JBL-LIVE-BLU', product:'JBL Live 770NC', brand:'JBL', category:'ANC Headphones', price:'₹9,999', inventory:31, variant:'Blue', delivery:'4 days', visible:true },
 { sku:'SENN-ACC-BLK', product:'Sennheiser Accentum', brand:'Sennheiser', category:'ANC Headphones', price:'₹12,499', inventory:9, variant:'Black', delivery:'3 days', visible:false },
]
export const transactions: Transaction[] = [
 { id:'TX-92881', intent:'INT-001', mandate:'MAN-001', agent:'buyer-agent-17', product:'Sony XM5', sku:'SONY-XM5-BLK', amount:'₹18,999', decision:'ALLOW', payment:'CAPTURED', created:'01:42:18' },
 { id:'TX-92880', intent:'INT-001', mandate:'MAN-001', agent:'buyer-agent-42', product:'Sony XM5 × 5', sku:'SONY-XM5-BLK', amount:'₹94,995', decision:'BLOCKED', payment:'NOT_SENT', created:'01:38:11', reason:'Quantity and amount exceed mandate' },
 { id:'TX-92870', intent:'INT-001', mandate:'MAN-001', agent:'buyer-agent-17', product:'Sony XM4', sku:'SONY-XM4-BLU', amount:'₹16,999', decision:'ALLOW', payment:'RECOVERED', created:'Yesterday' },
 { id:'TX-92878', intent:'INT-014', mandate:'MAN-014', agent:'procurement-agent-4', product:'AirPods Max', sku:'AIRPODS-MAX', amount:'₹32,999', decision:'STEP-UP', payment:'NOT_SENT', created:'Yesterday' },
]
export const navItems = [['Dashboard','/dashboard'],['Transactions','/transactions'],['Catalog','/catalog'],['Policies','/policies'],['Agents','/agents'],['Attack Lab','/attack-lab'],['Recovery','/recovery'],['Audit Log','/audit-log']] as const
export const auditEvents = [['01:42:03','Human Intent Approved','A871...'],['01:42:06','Agent Request Signed','B229...'],['01:42:07','Merchant Checkout Created','C801...'],['01:42:08','IntentLock ALLOW','D113...'],['01:42:09','Razorpay Order Created','E821...'],['01:42:18','Payment Captured','F922...']]
export const getTransaction = (id:string) => transactions.find(t=>t.id===id) ?? transactions[0]
export const money = (v:string) => v.replace('$','₹')
export const paths = new Set(['/onboard','/dashboard','/catalog','/transactions','/policies','/agents','/attack-lab','/recovery','/buyer-demo','/audit'])
export const faqs = [['What does IntentLock protect?','IntentLock verifies the agent, human authority, merchant charge, and execution before money moves.'],['Does it replace my payment processor?','No. It is the financial firewall above your existing payment environment.']]
export type Agent = { name:string; provider:string; trust:string; scope:string; status:string }
export const agents:Agent[] = [{name:'buyer-agent-17',provider:'Reference Buyer',trust:'VERIFIED',scope:'Sony ANC headphones · ₹20,000',status:'ACTIVE'},{name:'buyer-agent-42',provider:'Reference Buyer',trust:'SUSPENDED',scope:'No active mandates',status:'SUSPENDED'},{name:'procurement-agent-4',provider:'ProcureOS',trust:'UNKNOWN',scope:'Step-up required',status:'ACTIVE'}]
export const statusLabel = (value:string) => value.replaceAll('_',' ')
export const pipeline = ['Agent identity','Human mandate','Checkout integrity','Merchant policy','Replay protection','Idempotency']
export const policy = { max:'₹50,000', step:'₹25,000', daily:'₹1,00,000', discount:'5%', attempts:'2' }
export const canonical = { ...merchant, ...authority }
