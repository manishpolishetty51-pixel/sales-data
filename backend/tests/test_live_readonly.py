"""Read-only checks against the real MongoDB data. Skipped when no database is configured."""
import pytest
from fastapi.testclient import TestClient
from pymongo.errors import ServerSelectionTimeoutError

from config import get_settings
from main import app
from routers.inventory import get_service
from services.inventory_service import InventoryService
from tests.conftest import FakeCollection

import tests.conftest  # noqa: F401  (ensures API_KEY override is applied first)

uri = get_settings().mongodb_uri
live = pytest.mark.skipif(not uri or uri.startswith("your_"), reason="MONGODB_URI not configured")


@pytest.fixture
def live_client():
    return TestClient(app)


@live
def test_health_reports_connected(live_client):
    body = live_client.get("/api/health").json()
    assert body["status"] == "ok" and body["database"]["connected"]
    assert "mongodb" not in str(body).lower().replace("mongodb atlas", "")


@live
def test_list_paginates_and_never_returns_everything(live_client):
    body = live_client.get("/api/inventory?limit=5").json()
    assert len(body["items"]) == 5 and body["total"] >= 5
    assert live_client.get("/api/inventory?limit=101").status_code == 422
    page2 = live_client.get("/api/inventory?limit=5&skip=5").json()
    assert {i["id"] for i in body["items"]}.isdisjoint(i["id"] for i in page2["items"])


@live
def test_empty_search_result(live_client):
    body = live_client.get("/api/inventory/search?q=zzzz-no-such-product").json()
    assert body["items"] == [] and body["total"] == 0


@live
def test_stats_match_listing(live_client):
    stats = live_client.get("/api/inventory/stats").json()
    total = live_client.get("/api/inventory?limit=1").json()["total"]
    assert stats["totalItems"] == total
    low = live_client.get("/api/inventory/filter?status=low_stock&limit=100").json()["total"]
    assert stats["lowStockItems"] == low


def test_empty_collection_returns_zeroed_stats_and_list():
    svc = type("S", (InventoryService,), {})(FakeAggregating(), FakeCollection(), 10)
    assert svc.list_items() == {"items": [], "total": 0, "skip": 0, "limit": 20}
    assert svc.stats()["totalItems"] == 0


class FakeAggregating(FakeCollection):
    def aggregate(self, pipeline):
        return iter([] if not any("$facet" in s for s in pipeline) else [{"items": [], "total": []}])


def test_database_connection_failure_returns_503():
    from pymongo import MongoClient
    dead = MongoClient("mongodb://127.0.0.1:1", serverSelectionTimeoutMS=300)
    app.dependency_overrides[get_service] = lambda: InventoryService(
        dead["x"]["y"], dead["x"]["z"], 10)
    try:
        r = TestClient(app).get("/api/inventory/stats")
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 503
    assert "127.0.0.1" not in r.text and "mongodb://" not in r.text
