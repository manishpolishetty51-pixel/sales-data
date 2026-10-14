"""All inventory business logic and MongoDB queries.

Existing data model (neerus.inventory): integer `_id`/`id`, `sku`, `name`, `category`,
`price`, `cost`, `suppliers` (list of ids into the suppliers collection) and `stock`,
a dict of units per store. There is no stored quantity or status, so total units and
stock status are derived here.
"""
import re
from typing import Any

from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError

SORT_FIELDS = {"name", "sku", "price", "cost", "category", "totalStock"}
SEARCH_FIELDS = ("name", "sku", "category", "subCategory", "colour")


class ItemNotFound(Exception):
    pass


class DuplicateSku(Exception):
    pass


class InvalidQuery(Exception):
    pass


def total_units(stock: Any) -> int:
    if not isinstance(stock, dict):
        return 0
    return sum(v for v in stock.values() if isinstance(v, (int, float)) and not isinstance(v, bool))


def stock_status(total: int, threshold: int) -> str:
    if total <= 0:
        return "out_of_stock"
    if total <= threshold:
        return "low_stock"
    return "in_stock"


# --- MongoDB aggregation fragments (mirror total_units / stock_status) -------------

TOTAL_EXPR = {"$sum": {"$map": {
    "input": {"$objectToArray": {"$ifNull": ["$stock", {}]}},
    "as": "s", "in": "$$s.v"}}}


def status_expr(threshold: int) -> dict:
    return {"$switch": {
        "branches": [
            {"case": {"$lte": ["$totalStock", 0]}, "then": "out_of_stock"},
            {"case": {"$lte": ["$totalStock", threshold]}, "then": "low_stock"},
        ],
        "default": "in_stock"}}


def build_match(q: str | None, category: str | None, department: str | None) -> dict:
    """Safe filter: user text is regex-escaped and only ever used as a literal."""
    conditions: list[dict] = []
    if q:
        pattern = re.escape(q.strip())
        conditions.append({"$or": [{f: {"$regex": pattern, "$options": "i"}} for f in SEARCH_FIELDS]})
    if category:
        conditions.append({"category": category})
    if department:
        conditions.append({"department": department})
    return {"$and": conditions} if conditions else {}


def build_pipeline(threshold: int, *, q=None, category=None, department=None, status=None,
                   sort="name", order="asc", skip=0, limit=20) -> list[dict]:
    if sort not in SORT_FIELDS:
        raise InvalidQuery(f"sort must be one of {sorted(SORT_FIELDS)}")
    pipeline: list[dict] = [
        {"$match": build_match(q, category, department)},
        {"$addFields": {"totalStock": TOTAL_EXPR}},
        {"$addFields": {"stockStatus": status_expr(threshold)}},
    ]
    if status:
        pipeline.append({"$match": {"stockStatus": status}})
    pipeline += [
        {"$sort": {sort: 1 if order == "asc" else -1, "id": 1}},
        {"$facet": {"items": [{"$skip": skip}, {"$limit": limit}],
                    "total": [{"$count": "n"}]}},
    ]
    return pipeline


class InventoryService:
    def __init__(self, items: Collection, suppliers: Collection, low_stock_threshold: int):
        self.items = items
        self.suppliers = suppliers
        self.threshold = low_stock_threshold

    # --- helpers -------------------------------------------------------------------

    def _supplier_names(self, ids: set[int]) -> dict[int, str]:
        if not ids:
            return {}
        docs = self.suppliers.find({"id": {"$in": sorted(ids)}}, {"id": 1, "name": 1})
        return {d["id"]: d.get("name") for d in docs}

    def _present(self, doc: dict, names: dict[int, str]) -> dict:
        total = total_units(doc.get("stock"))
        out = {k: v for k, v in doc.items() if k not in ("_id", "size", "totalStock", "stockStatus")}
        out["suppliers"] = [{"id": s, "name": names.get(s)} for s in doc.get("suppliers") or []
                            if isinstance(s, int)]
        out["stock"] = {k: v for k, v in (doc.get("stock") or {}).items() if isinstance(v, int)}
        out["totalStock"] = total
        out["stockStatus"] = stock_status(total, self.threshold)
        return out

    def _present_many(self, docs: list[dict]) -> list[dict]:
        ids = {s for d in docs for s in d.get("suppliers") or [] if isinstance(s, int)}
        names = self._supplier_names(ids)
        return [self._present(d, names) for d in docs]

    def _sku_taken(self, sku: str, exclude_id: int | None = None) -> bool:
        query: dict = {"sku": sku}
        if exclude_id is not None:
            query["id"] = {"$ne": exclude_id}
        return self.items.find_one(query, {"id": 1}) is not None

    # --- reads ---------------------------------------------------------------------

    def list_items(self, *, q=None, category=None, department=None, status=None,
                   sort="name", order="asc", skip=0, limit=20) -> dict:
        pipeline = build_pipeline(self.threshold, q=q, category=category, department=department,
                                  status=status, sort=sort, order=order, skip=skip, limit=limit)
        facet = next(iter(self.items.aggregate(pipeline)), {"items": [], "total": []})
        total = facet["total"][0]["n"] if facet["total"] else 0
        return {"items": self._present_many(facet["items"]), "total": total,
                "skip": skip, "limit": limit}

    def get_item(self, item_id: int) -> dict:
        doc = self.items.find_one({"id": item_id})
        if doc is None:
            raise ItemNotFound(item_id)
        return self._present_many([doc])[0]

    def stats(self) -> dict:
        pipeline = [
            {"$addFields": {"totalStock": TOTAL_EXPR}},
            {"$addFields": {"stockStatus": status_expr(self.threshold)}},
            {"$group": {
                "_id": None,
                "totalItems": {"$sum": 1},
                "totalUnits": {"$sum": "$totalStock"},
                "lowStockItems": {"$sum": {"$cond": [{"$eq": ["$stockStatus", "low_stock"]}, 1, 0]}},
                "outOfStockItems": {"$sum": {"$cond": [{"$eq": ["$stockStatus", "out_of_stock"]}, 1, 0]}},
                "inventoryValueRetail": {"$sum": {"$multiply": ["$totalStock", "$price"]}},
                "inventoryValueCost": {"$sum": {"$multiply": ["$totalStock", "$cost"]}},
            }},
        ]
        row = next(iter(self.items.aggregate(pipeline)), {})
        keys = ("totalItems", "totalUnits", "lowStockItems", "outOfStockItems",
                "inventoryValueRetail", "inventoryValueCost")
        result = {k: int(row.get(k, 0)) for k in keys}
        result["lowStockThreshold"] = self.threshold
        return result

    def options(self) -> dict:
        stores = self.items.aggregate([
            {"$project": {"kv": {"$objectToArray": {"$ifNull": ["$stock", {}]}}}},
            {"$unwind": "$kv"},
            {"$group": {"_id": "$kv.k"}},
        ])
        suppliers = self.suppliers.find({}, {"id": 1, "name": 1}).sort("id", 1)
        return {
            "categories": sorted(c for c in self.items.distinct("category") if isinstance(c, str)),
            "departments": sorted(c for c in self.items.distinct("department") if isinstance(c, str)),
            "stores": sorted(s["_id"] for s in stores),
            "suppliers": [{"id": s["id"], "name": s.get("name")} for s in suppliers],
            "statuses": ["in_stock", "low_stock", "out_of_stock"],
            "lowStockThreshold": self.threshold,
        }

    # --- writes --------------------------------------------------------------------

    def create_item(self, data: dict) -> dict:
        if self._sku_taken(data["sku"]):
            raise DuplicateSku(data["sku"])
        for _ in range(5):  # retry if another writer takes the same id first
            last = next(iter(self.items.find({}, {"id": 1}).sort("id", -1).limit(1)), None)
            new_id = (last["id"] if last else 0) + 1
            doc = {"_id": new_id, "id": new_id, **data}
            try:
                self.items.insert_one(doc)
                return self.get_item(new_id)
            except DuplicateKeyError:
                continue
        raise DuplicateKeyError("could not allocate a unique id")

    def update_item(self, item_id: int, changes: dict) -> dict:
        if not changes:
            raise InvalidQuery("No fields to update.")
        if "sku" in changes and self._sku_taken(changes["sku"], exclude_id=item_id):
            raise DuplicateSku(changes["sku"])
        sets = {k: v for k, v in changes.items() if k != "stock"}
        for store, units in (changes.get("stock") or {}).items():
            sets[f"stock.{store}"] = units  # merge per store, leave other stores untouched
        result = self.items.update_one({"id": item_id}, {"$set": sets})
        if result.matched_count == 0:
            raise ItemNotFound(item_id)
        return self.get_item(item_id)

    def delete_item(self, item_id: int) -> None:
        if self.items.delete_one({"id": item_id}).deleted_count == 0:
            raise ItemNotFound(item_id)
