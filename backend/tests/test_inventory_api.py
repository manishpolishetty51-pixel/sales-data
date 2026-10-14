from tests.conftest import AUTH

NEW_ITEM = {"sku": "SKU-NEW", "name": "New Saree", "category": "Sarees", "department": "Women",
            "price": 1500, "cost": 900, "stock": {"A": 3, "B": 4}}


def test_get_item_resolves_supplier_and_derives_stock(client):
    body = client.get("/api/inventory/1").json()
    assert body["totalStock"] == 12 and body["stockStatus"] == "in_stock"
    assert body["suppliers"] == [{"id": 1, "name": "Acme Textiles"}]
    assert "_id" not in body


def test_out_of_stock_status(client):
    assert client.get("/api/inventory/2").json()["stockStatus"] == "out_of_stock"


def test_invalid_and_unknown_ids(client):
    assert client.get("/api/inventory/abc").status_code == 400
    assert client.get("/api/inventory/-1").status_code == 400
    assert client.get("/api/inventory/%7B%22%24ne%22%3A1%7D").status_code == 400
    assert client.get("/api/inventory/9999").status_code == 404


def test_writes_require_api_key(client):
    assert client.post("/api/inventory", json=NEW_ITEM).status_code == 401
    assert client.put("/api/inventory/1", json={"price": 5}, headers={"X-API-Key": "wrong"}).status_code == 401
    assert client.delete("/api/inventory/1").status_code == 401


def test_create_assigns_next_id(client, fake_items):
    r = client.post("/api/inventory", json=NEW_ITEM, headers=AUTH)
    assert r.status_code == 201
    assert r.json()["id"] == 3 and r.headers["location"] == "/api/inventory/3"
    assert fake_items.docs[3]["_id"] == 3


def test_create_duplicate_sku_conflicts(client):
    r = client.post("/api/inventory", json={**NEW_ITEM, "sku": "SKU-1"}, headers=AUTH)
    assert r.status_code == 409


def test_create_validation(client):
    bad = [{}, {**NEW_ITEM, "price": -1}, {**NEW_ITEM, "price": "abc"}, {**NEW_ITEM, "price": 1.5},
           {**NEW_ITEM, "stock": {"A": -2}}, {**NEW_ITEM, "stock": {"a.b": 1}},
           {**NEW_ITEM, "name": "   "}, {**NEW_ITEM, "_id": 99}, {**NEW_ITEM, "unknown": 1}]
    for payload in bad:
        assert client.post("/api/inventory", json=payload, headers=AUTH).status_code == 422, payload


def test_update_only_changes_sent_fields_and_merges_stock(client, fake_items):
    r = client.put("/api/inventory/1", json={"price": 250, "stock": {"A": 9}}, headers=AUTH)
    assert r.status_code == 200
    doc = fake_items.docs[1]
    assert doc["price"] == 250 and doc["stock"] == {"A": 9, "B": 7}
    assert doc["name"] == "Item 1" and doc["cost"] == 60  # untouched


def test_update_errors(client):
    assert client.put("/api/inventory/1", json={}, headers=AUTH).status_code == 400
    assert client.put("/api/inventory/9999", json={"price": 1}, headers=AUTH).status_code == 404
    assert client.put("/api/inventory/1", json={"sku": "SKU-2"}, headers=AUTH).status_code == 409
    assert client.put("/api/inventory/1", json={"sku": "SKU-1"}, headers=AUTH).status_code == 200  # own SKU ok
    assert client.put("/api/inventory/1", json={"price": None}, headers=AUTH).status_code == 422
    assert client.put("/api/inventory/1", json={"price": -5}, headers=AUTH).status_code == 422


def test_delete(client, fake_items):
    assert client.delete("/api/inventory/1", headers=AUTH).status_code == 204
    assert 1 not in fake_items.docs
    assert client.delete("/api/inventory/1", headers=AUTH).status_code == 404


def test_writes_disabled_when_key_unconfigured(client, monkeypatch):
    import security
    from config import Settings
    monkeypatch.setattr(security, "get_settings", lambda: Settings("", "", "", "", 10, (), ""))
    assert client.delete("/api/inventory/1", headers=AUTH).status_code == 503
