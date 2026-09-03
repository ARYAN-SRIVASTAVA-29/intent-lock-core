import io


def register(client, email="merchant@example.com", store="Test Audio Store"):
    r=client.post('/api/v1/auth/register',json={'store_name':store,'email':email,'password':'strongpass123'})
    assert r.status_code==201
    return r.json()


def onboard_until_discovery(client):
    client.post('/api/v1/onboarding/payment/test')
    client.post('/api/v1/catalog/demo')
    client.post('/api/v1/onboarding/policy/publish')
    client.post('/api/v1/onboarding/identity/provision')
    return client.post('/api/v1/agent-commerce/discovery/test')


def test_private_catalog_requires_auth(client):
    assert client.get('/api/v1/catalog/products').status_code==401


def test_new_merchant_can_become_discoverable(client):
    me=register(client,'discover@example.com','Discover Store')
    merchant_id=me['merchant']['merchant_id']
    response=onboard_until_discovery(client)
    assert response.status_code==200
    assert response.json()['result']=='DISCOVERABLE'
    public=client.get(f'/api/v1/agent-commerce/merchants/{merchant_id}/discovery')
    assert public.status_code==200
    assert public.json()['status']=='AI_TRANSACTABLE'
    assert public.json()['skus']==31


def test_catalog_upload_csv_is_merchant_scoped(client):
    me=register(client,'upload@example.com','CSV Store')
    csv=b"sku,product,brand,category,price,inventory,variant,visible\nSKU-1,Test Headphone,Acme,ANC Headphones,9999,5,Black,true\n"
    r=client.post('/api/v1/catalog/upload',files={'file':('catalog.csv',io.BytesIO(csv),'text/csv')})
    assert r.status_code==200
    assert r.json()['summary']['skus']==1
    assert r.json()['items'][0]['price_minor']==999900
    merchant_id=me['merchant']['merchant_id']
    current=client.get('/api/v1/agent-commerce/catalog')
    assert current.status_code==200
    assert current.json()['items'][0]['sku']=='SKU-1'
    public=client.get(f'/api/v1/agent-commerce/merchants/{merchant_id}/catalog')
    assert public.status_code==409


def test_console_completion_requires_all_readiness_checks(client):
    register(client,'notready@example.com','Not Ready Store')
    r=client.post('/api/v1/onboarding/complete')
    assert r.status_code==409


def test_completed_merchant_can_use_private_catalog(client):
    register(client,'complete@example.com','Complete Store')
    onboard_until_discovery(client)
    r=client.post('/api/v1/onboarding/complete')
    assert r.status_code==200
    assert r.json()['onboarding_completed'] is True
    c=client.get('/api/v1/catalog/products')
    assert c.status_code==200
    assert c.json()['summary']['skus']==31
