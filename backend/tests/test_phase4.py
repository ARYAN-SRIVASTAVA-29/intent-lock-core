import io


def register(client, email="phase4@example.com", store="Phase Four Store"):
    response = client.post(
        "/api/v1/auth/register",
        json={"store_name": store, "email": email, "password": "strongpass123"},
    )
    assert response.status_code == 201
    return response.json()


def complete_prerequisites(client):
    assert client.post("/api/v1/onboarding/payment/test").status_code == 200
    assert client.post("/api/v1/onboarding/policy/publish").status_code == 200
    assert client.post("/api/v1/onboarding/identity/provision").status_code == 200


def test_uploaded_catalog_counts_drive_control_plane(client):
    register(client, "counts@example.com", "Four Product Store")
    csv = b"""sku,product,brand,category,price,inventory,variant,visible
SKU-1,Alpha Headphone,Acme,Headphones,1000,5,Black,true
SKU-2,Beta Headphone,Acme,Headphones,2000,4,Blue,true
SKU-3,Gamma Speaker,SoundCo,Speakers,3000,3,Black,true
SKU-4,Delta Earbuds,BudsCo,Earbuds,4000,2,White,true
"""
    uploaded = client.post(
        "/api/v1/catalog/upload",
        files={"file": ("catalog.csv", io.BytesIO(csv), "text/csv")},
    )
    assert uploaded.status_code == 200
    summary = uploaded.json()["summary"]
    assert summary["products"] == 4
    assert summary["skus"] == 4
    assert summary["brands"] == 3
    assert summary["categories"] == 3
    assert summary["last_updated_at"] is not None

    control = client.get("/api/v1/merchant")
    assert control.status_code == 200
    assert control.json()["merchant_name"] == "Four Product Store"
    assert control.json()["catalog"]["products"] == 4
    assert control.json()["catalog"]["skus"] == 4


def test_identity_and_policy_are_real_merchant_state(client):
    register(client, "policy@example.com", "Policy Store")
    client.post("/api/v1/catalog/demo")
    complete_prerequisites(client)
    discovery = client.post("/api/v1/agent-commerce/discovery/test")
    assert discovery.status_code == 200
    assert discovery.json()["result"] == "DISCOVERABLE"
    assert client.post("/api/v1/onboarding/complete").status_code == 200

    merchant = client.get("/api/v1/merchant").json()
    assert merchant["identity_active"] is True
    assert merchant["identity_algorithm"] == "Ed25519"
    assert merchant["identity_fingerprint"].startswith("mk_")
    assert merchant["policy_version"] == "v1"

    current = client.get("/api/v1/policies/current")
    assert current.status_code == 200
    payload = current.json()
    payload.update(
        max_transaction_minor=7_500_000,
        step_up_above_minor=3_500_000,
        daily_spend_minor=15_000_000,
        max_discount_pct=7.5,
        max_recovery_attempts=3,
    )
    update_body = {
        key: payload[key]
        for key in [
            "max_transaction_minor",
            "step_up_above_minor",
            "daily_spend_minor",
            "max_discount_pct",
            "max_recovery_attempts",
            "alternative_skus_allowed",
            "merchant_switching_allowed",
            "unknown_agent_action",
        ]
    }
    saved = client.put("/api/v1/policies/current", json=update_body)
    assert saved.status_code == 200
    assert saved.json()["max_transaction_minor"] == 7_500_000
    assert client.get("/api/v1/policies/current").json()["max_recovery_attempts"] == 3


def test_public_agent_surface_opens_only_after_discovery_and_checkout_price_is_merchant_authoritative(client):
    me = register(client, "checkout@example.com", "Checkout Store")
    merchant_id = me["merchant"]["merchant_id"]
    csv = b"sku,product,brand,category,price,inventory,variant,visible\nSKU-X,Merchant Priced Item,Acme,Headphones,18999,5,Black,true\n"
    assert client.post(
        "/api/v1/catalog/upload",
        files={"file": ("catalog.csv", io.BytesIO(csv), "text/csv")},
    ).status_code == 200

    assert client.get(f"/api/v1/agent-commerce/merchants/{merchant_id}/catalog").status_code == 409
    complete_prerequisites(client)
    assert client.post("/api/v1/agent-commerce/discovery/test").json()["result"] == "DISCOVERABLE"

    public_catalog = client.get(f"/api/v1/agent-commerce/merchants/{merchant_id}/catalog")
    assert public_catalog.status_code == 200
    assert public_catalog.json()["summary"]["skus"] == 1

    checkout = client.post(
        f"/api/v1/agent-commerce/merchants/{merchant_id}/checkouts",
        json={"sku": "SKU-X", "quantity": 2},
    )
    assert checkout.status_code == 200
    body = checkout.json()
    assert body["unit_price_minor"] == 1_899_900
    assert body["total_minor"] == 3_799_800
    assert body["price_authority"] == "MERCHANT_CATALOG"
    assert body["status"] == "PROPOSED"
