"""Test fixtures. CRUD tests run against an in-memory fake collection so the live
MongoDB data is never written to. Tests marked `live` are strictly read-only."""
import copy
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from pymongo.errors import DuplicateKeyError

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ["API_KEY"] = "test-key"  # set before config is read

from config import get_settings  # noqa: E402
from main import app  # noqa: E402
from routers.sales import get_service  # noqa: E402
from services.sales_service import SalesService  # noqa: E402

get_settings.cache_clear()
AUTH = {"X-API-Key": "test-key"}


class FakeCursor(list):
    def sort(self, key, direction=1):
        keys = key if isinstance(key, list) else [(key, direction)]
        out = list(self)
        for k, d in reversed(keys):  # stable sorts, least significant key first
            out.sort(key=lambda doc: doc.get(k, 0), reverse=d == -1)
        return FakeCursor(out)

    def skip(self, n):
        return FakeCursor(self[n:])

    def limit(self, n):
        return FakeCursor(self[:n])


def _matches(doc, flt):
    for key, cond in flt.items():
        value = doc.get(key)
        if isinstance(cond, dict):
            if "$ne" in cond and value == cond["$ne"]:
                return False
        elif value != cond:
            return False
    return True


class FakeCollection:
    def __init__(self, docs=()):
        self.docs = {d["_id"]: copy.deepcopy(d) for d in docs}

    def find(self, flt=None, projection=None):
        return FakeCursor(copy.deepcopy(d) for d in self.docs.values() if _matches(d, flt or {}))

    def find_one(self, flt, projection=None):
        return next(iter(self.find(flt)), None)

    def count_documents(self, flt):
        return len(self.find(flt))

    def insert_one(self, doc):
        if doc["_id"] in self.docs:
            raise DuplicateKeyError("duplicate _id")
        self.docs[doc["_id"]] = copy.deepcopy(doc)

    def update_one(self, flt, update):
        doc = next((d for d in self.docs.values() if _matches(d, flt)), None)
        if doc is None:
            return SimpleNamespace(matched_count=0)
        doc.update(update["$set"])
        return SimpleNamespace(matched_count=1)

    def delete_one(self, flt):
        doc = next((d for d in self.docs.values() if _matches(d, flt)), None)
        if doc:
            del self.docs[doc["_id"]]
        return SimpleNamespace(deleted_count=1 if doc else 0)


def make_sale(i, at, lines=((1, 2, 100),), payment="Cash"):
    items = [{"id": n, "sku": f"SKU-{n}", "name": f"Product {n}", "category": "Sarees",
              "qty": q, "price": p} for n, q, p in lines]
    return {"_id": i, "id": i, "store": "Madhapur", "staff": "Asha", "at": float(at),
            "items": items, "total": sum(q * p for _, q, p in lines), "payment": payment}


@pytest.fixture
def fake_sales():
    return FakeCollection([make_sale(1, 1000), make_sale(2, 2000, ((3, 1, 500), (4, 2, 250)), "UPI"),
                           make_sale(3, 3000)])


@pytest.fixture
def client(fake_sales):
    app.dependency_overrides[get_service] = lambda: SalesService(fake_sales)
    yield TestClient(app)
    app.dependency_overrides.clear()
