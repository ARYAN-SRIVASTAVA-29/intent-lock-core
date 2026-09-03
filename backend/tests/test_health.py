def test_root(client) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["service"] == "intentlock"
    assert response.json()["version"] == "0.9.1"

def test_health(client) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["service"] == "intentlock"
