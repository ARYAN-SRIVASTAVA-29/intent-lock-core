
def setup_store(client,email='core@example.com'):
    r=client.post('/api/v1/auth/register',json={'store_name':'Core Store','email':email,'password':'strongpass123'})
    assert r.status_code==201
    assert client.post('/api/v1/onboarding/payment/test').status_code==200
    assert client.post('/api/v1/catalog/demo').status_code==200
    assert client.post('/api/v1/onboarding/policy/publish').status_code==200
    assert client.post('/api/v1/onboarding/identity/provision').status_code==200
    assert client.post('/api/v1/agent-commerce/discovery/test').status_code==200
    assert client.post('/api/v1/onboarding/complete').status_code==200


def test_real_transaction_allow_and_dashboard(client):
    setup_store(client,'allow@example.com')
    before=client.get('/api/v1/catalog/products').json()['items']
    before_inventory=next(item['inventory'] for item in before if item['sku']=='SONY-USBC-AUDIO')
    tx=client.post('/api/v1/transactions/demo',json={'sku':'SONY-USBC-AUDIO','quantity':1,'max_quantity':1,'max_amount_minor':300000,'payment_outcome':'CAPTURED'})
    assert tx.status_code==200,tx.text
    body=tx.json()
    assert body['decision']=='ALLOW'
    assert body['payment_state']=='CAPTURED'
    assert body['razorpay_api_calls']==0
    assert body['payment_order_id'].startswith('order_test_')
    assert body['inventory_after']==before_inventory-1
    after=client.get('/api/v1/catalog/products').json()['items']
    assert next(item['inventory'] for item in after if item['sku']=='SONY-USBC-AUDIO')==before_inventory-1
    assert all(c['result'] in {'PASS','STEP_UP'} for c in body['checks'])
    dash=client.get('/api/v1/dashboard')
    assert dash.status_code==200,dash.text
    data=dash.json()
    assert data['commerce']['economic_actions']>=1
    assert data['commerce']['captured_gmv_minor']>=199900
    assert data['enforcement']['allowed']>=1
    assert data['operations']['inventory']['committed_units']>=1
    assert data['operations']['funnel']['captured']>=1
    assert len(data['operations']['activity_7d'])==7


def test_inventory_commit_is_idempotent_and_failure_releases(client):
    setup_store(client,'inventory@example.com')
    before=client.get('/api/v1/catalog/products').json()['items']
    starting=next(item['inventory'] for item in before if item['sku']=='SONY-USBC-AUDIO')
    created=client.post('/api/v1/transactions/demo',json={'sku':'SONY-USBC-AUDIO','quantity':2,'max_quantity':2,'max_amount_minor':500000})
    assert created.status_code==200,created.text
    tx_id=created.json()['transaction_id']
    authorized=client.post(f'/api/v1/transactions/{tx_id}/payments/simulate',json={'outcome':'AUTHORIZED'})
    assert authorized.status_code==200,authorized.text
    assert authorized.json()['inventory_after']==starting-2
    captured=client.post(f'/api/v1/transactions/{tx_id}/payments/simulate',json={'outcome':'CAPTURED'})
    assert captured.status_code==200,captured.text
    assert captured.json()['inventory_after']==starting-2
    repeated=client.post(f'/api/v1/transactions/{tx_id}/payments/simulate',json={'outcome':'CAPTURED'})
    assert repeated.status_code==200,repeated.text
    assert repeated.json()['inventory_after']==starting-2

    second=client.post('/api/v1/transactions/demo',json={'sku':'SONY-USBC-AUDIO','quantity':1,'max_quantity':1,'max_amount_minor':300000})
    second_id=second.json()['transaction_id']
    client.post(f'/api/v1/transactions/{second_id}/payments/simulate',json={'outcome':'AUTHORIZED'})
    failed=client.post(f'/api/v1/transactions/{second_id}/payments/simulate',json={'outcome':'FAILED'})
    assert failed.status_code==200,failed.text
    assert failed.json()['inventory_after']==starting-2


def test_quantity_attack_is_blocked_before_razorpay(client):
    setup_store(client,'attack@example.com')
    r=client.post('/api/v1/attack-lab/run',json={'scenario':'Quantity Escalation'})
    assert r.status_code==200,r.text
    data=r.json()
    assert data['result']=='BLOCKED'
    assert data['razorpay_api_calls']==0
    assert 'MANDATE_QUANTITY_LIMIT' in data['transaction']['reason_codes']


def test_duplicate_invocation_one_payment_order(client):
    setup_store(client,'duplicate@example.com')
    r=client.post('/api/v1/attack-lab/run',json={'scenario':'Duplicate Invocation'})
    assert r.status_code==200,r.text
    data=r.json()
    assert data['result']=='CONTAINED'
    assert data['tool_requests']==3
    assert data['economic_actions']==1
    assert data['duplicates_prevented']==2
    assert data['razorpay_orders']==0
    assert data['payment_orders']==1


def test_replay_is_recorded_and_blocked(client):
    setup_store(client,'replay@example.com')
    r=client.post('/api/v1/attack-lab/run',json={'scenario':'Replay Mandate'})
    assert r.status_code==200,r.text
    data=r.json()
    assert data['result']=='BLOCKED'
    reasons=data['transaction']['reason_codes']
    assert 'REPLAY_DETECTED' in reasons
    assert 'MANDATE_ALREADY_CONSUMED' in reasons
    assert data['razorpay_api_calls']==0


def test_failed_payment_can_recover_inside_original_authority(client):
    setup_store(client,'recovery@example.com')
    first=client.post('/api/v1/transactions/demo',json={'sku':'SONY-USBC-AUDIO','quantity':1,'max_quantity':1,'max_amount_minor':300000,'payment_outcome':'FAILED'})
    assert first.status_code==200,first.text
    assert first.json()['payment_state']=='FAILED'
    cases=client.get('/api/v1/recovery').json()
    assert cases['open']==1
    case_id=cases['items'][0]['case_id']
    recovered=client.post(f'/api/v1/recovery/{case_id}/execute',json={'sku':'SONY-USBC-AUDIO','quantity':1})
    assert recovered.status_code==200,recovered.text
    assert recovered.json()['decision']=='ALLOW'
    assert recovered.json()['payment_state']=='RECOVERED'
    cases2=client.get('/api/v1/recovery').json()
    assert cases2['recovered']==1


def test_audit_chain_verifies(client):
    setup_store(client,'audit@example.com')
    client.post('/api/v1/transactions/demo',json={'sku':'SONY-USBC-AUDIO','quantity':1,'max_quantity':1,'max_amount_minor':300000,'payment_outcome':'CAPTURED'})
    r=client.post('/api/v1/audit/verify')
    assert r.status_code==200
    assert r.json()['verified'] is True
    assert r.json()['count']>=5

import pytest

@pytest.mark.parametrize('scenario,expected',[
    ('Prompt Injection','BLOCKED'),
    ('Wrong Product','BLOCKED'),
    ('Checkout Mutation','BLOCKED'),
    ('Wrong Merchant','BLOCKED'),
    ('Expired Authorization','BLOCKED'),
    ('Unauthorized Recovery','BLOCKED'),
])
def test_attack_lab_scenarios(client,scenario,expected):
    email='scenario-'+scenario.lower().replace(' ','-')+'@example.com'
    setup_store(client,email)
    r=client.post('/api/v1/attack-lab/run',json={'scenario':scenario})
    assert r.status_code==200,r.text
    assert r.json()['result']==expected
    tx=r.json()['transaction']
    assert tx['razorpay_api_calls']==0
    assert any(c['result']=='FAIL' for c in tx['checks'])

def test_reference_buyer_plans_from_real_catalog(client):
    setup_store(client,'buyerplan@example.com')
    r=client.post('/api/v1/buyer-agent/plan',json={'request':'Buy one Sony headphone under ₹20,000'})
    assert r.status_code==200,r.text
    body=r.json()
    assert body['agent_id']=='buyer-agent-17'
    assert body['brand']=='Sony'
    assert body['unit_price_minor']<=2_000_000
    assert 'search_catalog()' in body['tool_trace']


def test_reference_buyer_returns_ranked_multi_match_comparison(client):
    setup_store(client,'buyer-matches@example.com')
    response=client.post('/api/v1/buyer-agent/plan',json={'request':'Show me all headphones under ₹20,000'})
    assert response.status_code==200,response.text
    body=response.json()
    assert body['planning_mode']=='DETERMINISTIC_MULTI_MATCH'
    assert len(body['matches'])>=4
    assert body['recommended_sku']==body['matches'][0]['sku']
    assert all(item['total_minor']<=2_000_000 for item in body['matches'])
    assert all(item['inventory']>0 for item in body['matches'])


def test_attack_lab_custom_payload_is_editable_and_auditable(client):
    setup_store(client,'custom-attack@example.com')
    config=client.get('/api/v1/attack-lab/config')
    assert config.status_code==200,config.text
    authority=config.json()['authority']
    response=client.post('/api/v1/attack-lab/run',json={
        'scenario':'Custom Payload',
        'sku':authority['sku'],
        'quantity':7,
        'asserted_total_minor':authority['max_amount_minor']*7,
        'merchant_override':config.json()['merchant_id'],
    })
    assert response.status_code==200,response.text
    body=response.json()
    assert body['result']=='BLOCKED'
    assert body['submitted_payload']['quantity']==7
    assert body['razorpay_api_calls']==0
    assert 'MANDATE_QUANTITY_LIMIT' in body['transaction']['reason_codes']


def test_recovery_center_returns_authority_scored_candidates(client):
    setup_store(client,'recovery-candidates@example.com')
    first=client.post('/api/v1/transactions/demo',json={'sku':'SONY-USBC-AUDIO','quantity':1,'max_quantity':1,'max_amount_minor':300000,'payment_outcome':'FAILED'})
    assert first.status_code==200,first.text
    cases=client.get('/api/v1/recovery')
    assert cases.status_code==200,cases.text
    record=cases.json()['items'][0]
    assert record['authority']['max_quantity']==1
    assert any(candidate['sku']=='SONY-USBC-AUDIO' and candidate['eligible'] for candidate in record['candidates'])
    assert any(not candidate['eligible'] and candidate['reason_codes'] for candidate in record['candidates'])


def test_payment_config_is_explicitly_local_without_account_keys(client):
    response=client.get('/api/v1/payments/config')
    assert response.status_code==200,response.text
    body=response.json()
    assert body['mode']=='LOCAL_TEST'
    assert body['credentials_state']=='NOT_CONFIGURED'
    assert body['razorpay_enabled'] is False
    assert body['key_id'] is None


def test_step_up_never_creates_payment_order(client):
    setup_store(client,'stepup@example.com')
    # AirPods Max is above default merchant step-up threshold but within human max.
    r=client.post('/api/v1/transactions/demo',json={'sku':'AIRPODS-MAX','quantity':1,'max_quantity':1,'max_amount_minor':4_000_000})
    assert r.status_code==200,r.text
    body=r.json()
    assert body['decision']=='STEP-UP'
    assert body['razorpay_api_calls']==0
    assert body['payment_order_id'] is None


def test_dashboard_contains_only_real_zero_or_recorded_metrics(client):
    setup_store(client,'dashzero@example.com')
    before=client.get('/api/v1/dashboard').json()
    assert before['commerce']['economic_actions']==0
    assert before['enforcement']['blocked']==0
    client.post('/api/v1/attack-lab/run',json={'scenario':'Quantity Escalation'})
    after=client.get('/api/v1/dashboard').json()
    assert after['commerce']['economic_actions']==1
    assert after['enforcement']['blocked']==1


def test_audit_verification_detects_tampering(client):
    r=client.post('/api/v1/auth/register',json={'store_name':'Tamper Store','email':'tamper@example.com','password':'strongpass123'})
    assert r.status_code==201
    merchant_id=r.json()['merchant']['merchant_id']
    assert client.post('/api/v1/onboarding/payment/test').status_code==200
    assert client.post('/api/v1/catalog/demo').status_code==200
    assert client.post('/api/v1/onboarding/policy/publish').status_code==200
    assert client.post('/api/v1/onboarding/identity/provision').status_code==200
    assert client.post('/api/v1/agent-commerce/discovery/test').status_code==200
    assert client.post('/api/v1/onboarding/complete').status_code==200
    client.post('/api/v1/transactions/demo',json={'sku':'SONY-USBC-AUDIO','quantity':1,'max_quantity':1,'max_amount_minor':300000})
    from app.db.session import SessionLocal
    from app.models import AuditEvent
    from sqlalchemy import select
    with SessionLocal() as db:
        event=db.scalar(select(AuditEvent).where(AuditEvent.merchant_id==merchant_id).order_by(AuditEvent.sequence.asc()))
        assert event is not None
        event.event_hash='0'*64;db.commit()
    verified=client.post('/api/v1/audit/verify').json()
    assert verified['verified'] is False
    assert verified['failed_sequence'] is not None

def test_step_up_can_be_explicitly_approved_by_authenticated_merchant(client):
    setup_store(client,'stepupapprove@example.com')
    r=client.post('/api/v1/transactions/demo',json={'sku':'AIRPODS-MAX','quantity':1,'max_quantity':1,'max_amount_minor':4_000_000})
    assert r.status_code==200
    tx=r.json()
    assert tx['decision']=='STEP-UP'
    approved=client.post(f"/api/v1/transactions/{tx['transaction_id']}/step-up/approve")
    assert approved.status_code==200,approved.text
    body=approved.json()
    assert body['decision']=='ALLOW'
    assert body['razorpay_api_calls']==0
    assert body['payment_order_id'].startswith('order_test_')
    assert any(c['name']=='Human Step-Up Approval' and c['result']=='PASS' for c in body['checks'])

def test_mobile_store_end_to_end_user_story(client):
    r=client.post('/api/v1/auth/register',json={'store_name':'Mobile World','email':'mobileworld@example.com','password':'strongpass123'})
    assert r.status_code==201
    assert client.post('/api/v1/onboarding/payment/test').status_code==200
    csv=b'''sku,product,brand,category,price,inventory,variant,visible,delivery_days,currency\nSAM-A15-128,Samsung Galaxy A15,Samsung,Smartphones,15999,8,Black / 128GB,true,2,INR\nONE-NORD-256,OnePlus Nord CE,OnePlus,Smartphones,24999,6,Blue / 256GB,true,2,INR\nAPL-IP15-128,Apple iPhone 15,Apple,Smartphones,59900,4,Black / 128GB,true,3,INR\nBUDS-01,Store Buds,Acme,Accessories,1999,20,Black,true,1,INR\n'''
    import io
    up=client.post('/api/v1/catalog/upload',files={'file':('mobile.csv',io.BytesIO(csv),'text/csv')})
    assert up.status_code==200,up.text
    assert up.json()['summary']['products']==4
    assert client.post('/api/v1/onboarding/policy/publish').status_code==200
    assert client.post('/api/v1/onboarding/identity/provision').status_code==200
    assert client.post('/api/v1/agent-commerce/discovery/test').status_code==200
    assert client.post('/api/v1/onboarding/complete').status_code==200
    plan=client.post('/api/v1/buyer-agent/plan',json={'request':'Buy one Samsung phone under ₹20,000'}).json()
    assert plan['sku']=='SAM-A15-128'
    tx=client.post('/api/v1/transactions/demo',json={'sku':plan['sku'],'quantity':plan['quantity'],'max_quantity':plan['quantity'],'max_amount_minor':plan['max_amount_minor'],'natural_language':plan['request']})
    assert tx.status_code==200,tx.text
    assert tx.json()['decision']=='ALLOW'
    assert tx.json()['unit_price_minor']==1_599_900
    cap=client.post(f"/api/v1/transactions/{tx.json()['transaction_id']}/payments/simulate",json={'outcome':'CAPTURED'})
    assert cap.status_code==200
    attack=client.post('/api/v1/attack-lab/run',json={'scenario':'Quantity Escalation'}).json()
    assert attack['result']=='BLOCKED'
    dash=client.get('/api/v1/dashboard').json()
    assert dash['merchant']['catalog']['skus']==4
    assert dash['commerce']['economic_actions']>=2
    assert dash['enforcement']['blocked']>=1

def test_discovery_advertises_public_transaction_endpoint(client):
    setup_store(client,'transactable@example.com')
    discovery=client.get('/api/v1/agent-commerce/discovery').json()
    assert discovery['status']=='AI_TRANSACTABLE'
    assert discovery['transaction_endpoint'].endswith('/transactions')


def test_registered_external_agent_can_execute_signed_public_transaction(client):
    setup_store(client, 'external-agent@example.com')
    from app.services.crypto import canonical_json, generate_ed25519_keypair, sign_text
    import time
    import uuid

    private_key, public_key = generate_ed25519_keypair()
    agent_id = 'external-buyer-42'
    registered = client.post('/api/v1/agents', json={
        'agent_id': agent_id,
        'provider': 'External Test Agent',
        'public_key': public_key,
    })
    assert registered.status_code == 201, registered.text

    intent = client.post('/api/v1/intents/compile', json={
        'natural_language': 'Buy one Sony audio item under ₹3,000',
        'sku': 'SONY-USBC-AUDIO',
        'max_amount_minor': 300_000,
        'max_quantity': 1,
    })
    assert intent.status_code == 200, intent.text
    intent_id = intent.json()['intent_id']

    mandate = client.post('/api/v1/mandates', json={
        'intent_id': intent_id,
        'agent_id': agent_id,
        'expires_minutes': 120,
    })
    assert mandate.status_code == 200, mandate.text
    mandate_id = mandate.json()['mandate_id']

    discovery = client.get('/api/v1/agent-commerce/discovery').json()
    merchant_id = discovery['merchant_id']
    checkout = client.post(
        f'/api/v1/agent-commerce/merchants/{merchant_id}/checkouts',
        json={'sku': 'SONY-USBC-AUDIO', 'quantity': 1},
    )
    assert checkout.status_code == 200, checkout.text
    checkout_body = checkout.json()

    timestamp = int(time.time())
    nonce = f'ext_{uuid.uuid4().hex}'
    signed_body = {
        'agent_id': agent_id,
        'mandate_id': mandate_id,
        'sku': 'SONY-USBC-AUDIO',
        'quantity': 1,
        'checkout_id': checkout_body['checkout_id'],
        'checkout_hash': checkout_body['checkout_hash'],
        'nonce': nonce,
        'timestamp': timestamp,
    }
    signature = sign_text(private_key, canonical_json(signed_body))
    response = client.post(
        f'/api/v1/agent-commerce/merchants/{merchant_id}/transactions',
        json={
            'intent_id': intent_id,
            'mandate_id': mandate_id,
            'sku': 'SONY-USBC-AUDIO',
            'quantity': 1,
            'checkout_id': checkout_body['checkout_id'],
            'checkout_hash': checkout_body['checkout_hash'],
            'agent_id': agent_id,
            'nonce': nonce,
            'timestamp': timestamp,
            'signature': signature,
            'idempotency_key': f'external_{uuid.uuid4().hex}',
        },
    )
    assert response.status_code == 200, response.text
    tx = response.json()
    assert tx['decision'] == 'ALLOW'
    assert tx['agent_id'] == agent_id
    assert tx['checkout_id'] == checkout_body['checkout_id']
    assert tx['checkout_hash'] == checkout_body['checkout_hash']
    identity = next(c for c in tx['checks'] if c['name'] == 'Agent Identity')
    integrity = next(c for c in tx['checks'] if c['name'] == 'Checkout Integrity')
    binding = next(c for c in tx['checks'] if c['name'] == 'Mandate Binding')
    assert identity['result'] == 'PASS'
    assert integrity['result'] == 'PASS'
    assert binding['result'] == 'PASS'


def test_checkout_mutation_is_not_confused_with_bad_agent_signature(client):
    setup_store(client, 'checkout-integrity@example.com')
    response = client.post('/api/v1/attack-lab/run', json={'scenario': 'Checkout Mutation'})
    assert response.status_code == 200, response.text
    tx = response.json()['transaction']
    checks = {check['name']: check for check in tx['checks']}
    assert checks['Agent Identity']['result'] == 'PASS'
    assert checks['Checkout Integrity']['result'] == 'FAIL'
    assert checks['Checkout Integrity']['reason_code'] == 'CHECKOUT_MUTATED'
    assert tx['razorpay_api_calls'] == 0


def test_forged_agent_signature_is_blocked_before_payment(client):
    setup_store(client, 'forged-signature@example.com')
    response = client.post('/api/v1/attack-lab/run', json={'scenario': 'Forged Agent Signature'})
    assert response.status_code == 200, response.text
    tx = response.json()['transaction']
    checks = {check['name']: check for check in tx['checks']}
    assert tx['decision'] == 'BLOCKED'
    assert checks['Agent Identity']['result'] == 'FAIL'
    assert checks['Agent Identity']['reason_code'] == 'AGENT_SIGNATURE_INVALID'
    assert tx['razorpay_api_calls'] == 0
