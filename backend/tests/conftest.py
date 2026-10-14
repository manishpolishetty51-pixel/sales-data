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
from routers.inventory import get_service  # noqa: E402
from services.inventory_service import InventoryService  # noqa: E402

get_settings.cache_clear()
AUTH = {"X-API-Key": "test-key"}


class FakeCursor(list):
    def sort(self, key, direction=1):
        return FakeCursor(sorted(self, key=lambda d: d.get(key, 0), reverse=direction == -1))

    def limit(self, n):
        return FakeCursor(self[:n])


def _matches(doc, flt):
    for key, cond in flt.items():
        value = doc.get(key)
        if isinstance(cond, dict):
            if "$ne" in cond and value == cond["$ne"]:
                return False
            if "$in" in cond and value not in cond["$in"]:
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

    def insert_one(self, doc):
        if doc["_id"] in self.docs:
            raise DuplicateKeyError("duplicate _id")
        self.docs[doc["_id"]] = copy.deepcopy(doc)

    def update_one(self, flt, update):
        doc = next((d for d in self.docs.values() if _matches(d, flt)), None)
        if doc is None:
            return SimpleNamespace(matched_count=0)
        for path, value in update["$set"].items():
            target = doc
            *parents, last = path.split(".")
            for p in parents:
                target = target.setdefault(p, {})
            target[last] = value
        return SimpleNamespace(matched_count=1)

    def delete_one(self, flt):
        doc = next((d for d in self.docs.values() if _matches(d, flt)), None)
        if doc:
            del self.docs[doc["_id"]]
        return SimpleNamespace(deleted_count=1 if doc else 0)


def make_item(i, sku, stock=None):
    return {"_id": i, "id": i, "sku": sku, "name": f"Item {i}", "category": "Sarees",
            "department": "Women", "price": 100, "cost": 60, "suppliers": [1],
            "stock": stock or {"A": 5, "B": 7}, "size": None}


@pytest.fixture
def fake_items():
    return FakeCollection([make_item(1, "SKU-1"), make_item(2, "SKU-2", {"A": 0, "B": 0})])


@pytest.fixture
def client(fake_items):
    suppliers = FakeCollection([{"_id": 1, "id": 1, "name": "Acme Textiles"}])
    app.dependency_overrides[get_service] = lambda: InventoryService(fake_items, suppliers, 10)
    yield TestClient(app)
    app.dependency_overrides.clear()
