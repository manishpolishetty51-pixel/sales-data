from tests.conftest import AUTH

NEW_SALE = {"store": "Madhapur", "staff": "Asha", "payment": "Card",
            "items": [{"id": 5, "sku": "SKU-5", "name": "Product 5", "category": "Sarees",
                       "qty": 3, "price": 200},
                      {"id": 6, "sku": "SKU-6", "name": "Product 6", "category": "Sarees",
                       "qty": 1, "price": 50}]}


def test_get_sale_derives_counts(client):
    body = client.get("/api/sales/2").json()
    assert body["total"] == 1000 and body["unitCount"] == 3 and body["lineCount"] == 2
    assert "_id" not in body


def test_list_is_newest_first_and_paginated(client):
    body = client.get("/api/sales?limit=2").json()
    assert [s["id"] for s in body["sales"]] == [3, 2] and body["total"] == 3
    page2 = client.get("/api/sales?limit=2&skip=2").json()
    assert [s["id"] for s in page2["sales"]] == [1]
    asc = client.get("/api/sales?order=asc&sort=total").json()
    assert [s["total"] for s in asc["sales"]] == sorted(s["total"] for s in asc["sales"])


def test_invalid_query_parameters(client):
    for url in ["/api/sales?limit=0", "/api/sales?limit=101", "/api/sales?skip=-1",
                "/api/sales?sort=$where", "/api/sales?order=sideways", "/api/sales/search"]:
        assert client.get(url).status_code == 422, url
    assert client.get("/api/sales?start=5000&end=1000").status_code == 400


def test_invalid_and_unknown_ids(client):
    assert client.get("/api/sales/abc").status_code == 400
    assert client.get("/api/sales/-1").status_code == 400
    assert client.get("/api/sales/9999").status_code == 404


def test_writes_require_api_key(client):
    assert client.post("/api/sales", json=NEW_SALE).status_code == 401
    assert client.put("/api/sales/1", json={"staff": "X"}, headers={"X-API-Key": "wrong"}).status_code == 401
    assert client.delete("/api/sales/1").status_code == 401


def test_create_computes_total_and_assigns_id(client, fake_sales):
    r = client.post("/api/sales", json=NEW_SALE, headers=AUTH)
    assert r.status_code == 201
    body = r.json()
    assert body["id"] == 4 and body["total"] == 650 and body["unitCount"] == 4
    assert r.headers["location"] == "/api/sales/4"
    assert fake_sales.docs[4]["_id"] == 4 and isinstance(fake_sales.docs[4]["at"], float)


def test_create_rejects_client_total_and_bad_input(client):
    bad = [{}, {**NEW_SALE, "total": 1}, {**NEW_SALE, "items": []}, {**NEW_SALE, "payment": "Bitcoin"},
           {**NEW_SALE, "store": "  "}, {**NEW_SALE, "_id": 9}, {**NEW_SALE, "extra": 1},
           {**NEW_SALE, "items": [{**NEW_SALE["items"][0], "qty": 0}]},
           {**NEW_SALE, "items": [{**NEW_SALE["items"][0], "qty": 1.5}]},
           {**NEW_SALE, "items": [{**NEW_SALE["items"][0], "price": -1}]},
           {**NEW_SALE, "items": [{**NEW_SALE["items"][0], "price": "abc"}]}]
    for payload in bad:
        assert client.post("/api/sales", json=payload, headers=AUTH).status_code == 422, payload


def test_update_changes_only_sent_fields(client, fake_sales):
    r = client.put("/api/sales/1", json={"staff": "Ravi", "payment": "UPI"}, headers=AUTH)
    assert r.status_code == 200
    doc = fake_sales.docs[1]
    assert doc["staff"] == "Ravi" and doc["payment"] == "UPI"
    assert doc["store"] == "Madhapur" and doc["total"] == 200  # untouched


def test_update_items_recalculates_total(client, fake_sales):
    r = client.put("/api/sales/1", json={"items": NEW_SALE["items"]}, headers=AUTH)
    assert r.json()["total"] == 650 and fake_sales.docs[1]["total"] == 650


def test_update_errors(client):
    assert client.put("/api/sales/1", json={}, headers=AUTH).status_code == 400
    assert client.put("/api/sales/9999", json={"staff": "X"}, headers=AUTH).status_code == 404
    assert client.put("/api/sales/1", json={"payment": None}, headers=AUTH).status_code == 422
    assert client.put("/api/sales/1", json={"total": 1}, headers=AUTH).status_code == 422
    assert client.put("/api/sales/1", json={"items": []}, headers=AUTH).status_code == 422


def test_delete(client, fake_sales):
    assert client.delete("/api/sales/1", headers=AUTH).status_code == 204
    assert 1 not in fake_sales.docs
    assert client.delete("/api/sales/1", headers=AUTH).status_code == 404


def test_writes_disabled_when_key_unconfigured(client, monkeypatch):
    import security
    from config import Settings
    monkeypatch.setattr(security, "get_settings", lambda: Settings("", "", "", (), ""))
    assert client.delete("/api/sales/1", headers=AUTH).status_code == 503
