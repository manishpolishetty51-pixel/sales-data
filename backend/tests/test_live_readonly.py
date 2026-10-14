"""Read-only checks against the real MongoDB data. Skipped when no database is configured."""
import pytest
from fastapi.testclient import TestClient
from pymongo import MongoClient

from config import get_settings
from main import app
from routers.sales import get_service
from services.sales_service import SalesService
from tests.conftest import FakeCollection

uri = get_settings().mongodb_uri
live = pytest.mark.skipif(not uri or uri.startswith("your_"), reason="MONGODB_URI not configured")


@pytest.fixture
def live_client():
    return TestClient(app)


@live
def test_health_reports_connected(live_client):
    body = live_client.get("/api/health").json()
    assert body["status"] == "ok" and body["database"]["collection"] == "sales"


@live
def test_list_paginates_and_never_returns_everything(live_client):
    body = live_client.get("/api/sales?limit=5").json()
    assert len(body["sales"]) == 5 and body["total"] > 5
    assert live_client.get("/api/sales?limit=101").status_code == 422
    page2 = live_client.get("/api/sales?limit=5&skip=5").json()
    assert {s["id"] for s in body["sales"]}.isdisjoint(s["id"] for s in page2["sales"])
    times = [s["at"] for s in body["sales"]]
    assert times == sorted(times, reverse=True)


@live
def test_totals_match_line_items(live_client):
    for sale in live_client.get("/api/sales?limit=100").json()["sales"]:
        assert sale["total"] == sum(i["qty"] * i["price"] for i in sale["items"])


@live
def test_empty_search_result(live_client):
    body = live_client.get("/api/sales/search?q=zzzz-no-such-sale").json()
    assert body["sales"] == [] and body["total"] == 0


@live
def test_stats_are_consistent(live_client):
    stats = live_client.get("/api/sales/stats").json()
    assert stats["totalSales"] == live_client.get("/api/sales?limit=1").json()["total"]
    assert sum(r["count"] for r in stats["byPayment"]) == stats["totalSales"]
    assert sum(r["revenue"] for r in stats["byStore"]) == stats["totalRevenue"]
    assert stats["averageSale"] == round(stats["totalRevenue"] / stats["totalSales"])
    card = live_client.get("/api/sales/filter?payment=Card&limit=1").json()["total"]
    assert card == next(r["count"] for r in stats["byPayment"] if r["name"] == "Card")


@live
def test_date_range_filter(live_client):
    all_sales = live_client.get("/api/sales?limit=100&sort=at&order=asc").json()["sales"]
    mid = all_sales[50]["at"]
    body = live_client.get(f"/api/sales?end={int(mid)}&limit=100").json()
    assert body["total"] > 0 and all(s["at"] <= mid for s in body["sales"])


class _EmptyAggregating(FakeCollection):
    def aggregate(self, pipeline):
        return iter([{"overall": [], "byPayment": [], "byStore": []}])


def test_empty_collection_returns_zeroed_results():
    svc = SalesService(_EmptyAggregating())
    assert svc.list_sales() == {"sales": [], "total": 0, "skip": 0, "limit": 20}
    stats = svc.stats()
    assert stats["totalSales"] == 0 and stats["averageSale"] == 0 and stats["byStore"] == []


def test_database_connection_failure_returns_503():
    dead = MongoClient("mongodb://127.0.0.1:1", serverSelectionTimeoutMS=300)
    app.dependency_overrides[get_service] = lambda: SalesService(dead["x"]["y"])
    try:
        r = TestClient(app).get("/api/sales/stats")
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 503
    assert "127.0.0.1" not in r.text and "mongodb://" not in r.text
