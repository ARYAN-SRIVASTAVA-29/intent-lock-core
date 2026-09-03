def test_register_login_logout_and_console_gate(client):
    reg=client.post('/api/v1/auth/register',json={'store_name':'Aryan Electronics','email':'aryan@example.com','password':'password123'})
    assert reg.status_code==201
    body=reg.json()
    assert body['merchant']['merchant_name']=='Aryan Electronics'
    assert body['merchant']['onboarding_completed'] is False
    assert client.get('/api/v1/auth/me').status_code==200
    assert client.get('/api/v1/catalog/products').status_code==403
    assert client.post('/api/v1/auth/logout').status_code==200
    assert client.get('/api/v1/auth/me').status_code==401
    login=client.post('/api/v1/auth/login',json={'email':'aryan@example.com','password':'password123'})
    assert login.status_code==200


def test_duplicate_registration_rejected(client):
    payload={'store_name':'One Store','email':'dup@example.com','password':'password123'}
    assert client.post('/api/v1/auth/register',json=payload).status_code==201
    client.post('/api/v1/auth/logout')
    assert client.post('/api/v1/auth/register',json=payload).status_code==409
