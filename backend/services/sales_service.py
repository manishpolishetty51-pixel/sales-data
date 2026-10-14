"""All sales business logic and MongoDB queries.

Existing data model (neerus.sales): integer `_id`/`id`, `store`, `staff`, `at` (epoch
milliseconds), `payment` (Cash/Card/UPI), `total` and `items`, a list of line items
{id, sku, name, category, qty, price}. `total` always equals sum(qty * price); the
server recalculates it on every write instead of trusting the client.
"""
import re
import time

from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError

SORT_FIELDS = {"at", "total", "store", "staff", "payment", "id"}
PAYMENT_METHODS = ("Cash", "Card", "UPI")


class SaleNotFound(Exception):
    pass


class InvalidQuery(Exception):
    pass


def unit_count(items) -> int:
    if not isinstance(items, list):
        return 0
    return sum(i["qty"] for i in items
               if isinstance(i, dict) and isinstance(i.get("qty"), int) and not isinstance(i["qty"], bool))


def compute_total(items: list[dict]) -> int:
    return sum(i["qty"] * i["price"] for i in items)


def build_match(q=None, store=None, payment=None, staff=None, start=None, end=None) -> dict:
    """Safe filter: user text is regex-escaped and only ever used as a literal."""
    if start is not None and end is not None and start > end:
        raise InvalidQuery("start must not be after end.")
    conditions: list[dict] = []
    if q:
        text = q.strip()
        pattern = re.escape(text)
        ors = [{f: {"$regex": pattern, "$options": "i"}}
               for f in ("staff", "store", "items.name", "items.sku", "items.category")]
        if text.isascii() and text.isdigit() and len(text) <= 12:
            ors.append({"id": int(text)})
        conditions.append({"$or": ors})
    if store:
        conditions.append({"store": store})
    if payment:
        conditions.append({"payment": payment})
    if staff:
        conditions.append({"staff": staff})
    if start is not None or end is not None:
        rng: dict = {}
        if start is not None:
            rng["$gte"] = start
        if end is not None:
            rng["$lte"] = end
        conditions.append({"at": rng})
    return {"$and": conditions} if conditions else {}


class SalesService:
    def __init__(self, sales: Collection):
        self.sales = sales

    @staticmethod
    def _present(doc: dict) -> dict:
        items = [i for i in doc.get("items") or [] if isinstance(i, dict)]
        out = {k: v for k, v in doc.items() if k != "_id"}
        out["items"] = items
        out["unitCount"] = unit_count(items)
        out["lineCount"] = len(items)
        return out

    # --- reads ---------------------------------------------------------------------

    def list_sales(self, *, q=None, store=None, payment=None, staff=None, start=None, end=None,
                   sort="at", order="desc", skip=0, limit=20) -> dict:
        if sort not in SORT_FIELDS:
            raise InvalidQuery(f"sort must be one of {sorted(SORT_FIELDS)}")
        flt = build_match(q, store, payment, staff, start, end)
        direction = 1 if order == "asc" else -1
        cursor = (self.sales.find(flt).sort([(sort, direction), ("id", 1)]).skip(skip).limit(limit))
        return {"sales": [self._present(d) for d in cursor],
                "total": self.sales.count_documents(flt), "skip": skip, "limit": limit}

    def get_sale(self, sale_id: int) -> dict:
        doc = self.sales.find_one({"id": sale_id})
        if doc is None:
            raise SaleNotFound(sale_id)
        return self._present(doc)

    def stats(self, start=None, end=None) -> dict:
        def group(key):
            return [{"$group": {"_id": key, "count": {"$sum": 1}, "revenue": {"$sum": "$total"}}},
                    {"$sort": {"revenue": -1}}]

        pipeline = [
            {"$match": build_match(start=start, end=end)},
            {"$facet": {
                "overall": [{"$group": {
                    "_id": None, "n": {"$sum": 1}, "revenue": {"$sum": "$total"},
                    "units": {"$sum": {"$sum": "$items.qty"}},
                    "first": {"$min": "$at"}, "last": {"$max": "$at"}}}],
                "byPayment": group("$payment"),
                "byStore": group("$store"),
            }},
        ]
        res = next(iter(self.sales.aggregate(pipeline)), {})
        overall = (res.get("overall") or [{}])[0]
        n, revenue = int(overall.get("n", 0)), int(overall.get("revenue", 0))

        def rows(key):
            return [{"name": r["_id"], "count": r["count"], "revenue": int(r["revenue"])}
                    for r in res.get(key, [])]

        return {"totalSales": n, "totalRevenue": revenue,
                "averageSale": round(revenue / n) if n else 0,
                "unitsSold": int(overall.get("units", 0)),
                "firstSaleAt": overall.get("first"), "lastSaleAt": overall.get("last"),
                "byPayment": rows("byPayment"), "byStore": rows("byStore")}

    def options(self) -> dict:
        def names(field):
            return sorted(v for v in self.sales.distinct(field) if isinstance(v, str))

        return {"stores": names("store"), "staff": names("staff"),
                "payments": sorted(set(names("payment")) | set(PAYMENT_METHODS))}

    # --- writes --------------------------------------------------------------------

    def create_sale(self, data: dict) -> dict:
        data = dict(data)
        data["at"] = float(data.get("at") or time.time() * 1000)
        data["total"] = compute_total(data["items"])
        for _ in range(5):  # retry if another writer takes the same id first
            last = next(iter(self.sales.find({}, {"id": 1}).sort("id", -1).limit(1)), None)
            new_id = (last["id"] if last else 0) + 1
            doc = {"_id": new_id, "id": new_id, "store": data["store"], "staff": data["staff"],
                   "at": data["at"], "items": data["items"], "total": data["total"],
                   "payment": data["payment"]}
            try:
                self.sales.insert_one(doc)
                return self.get_sale(new_id)
            except DuplicateKeyError:
                continue
        raise DuplicateKeyError("could not allocate a unique id")

    def update_sale(self, sale_id: int, changes: dict) -> dict:
        if not changes:
            raise InvalidQuery("No fields to update.")
        changes = dict(changes)
        if "items" in changes:
            changes["total"] = compute_total(changes["items"])
        if "at" in changes:
            changes["at"] = float(changes["at"])
        if self.sales.update_one({"id": sale_id}, {"$set": changes}).matched_count == 0:
            raise SaleNotFound(sale_id)
        return self.get_sale(sale_id)

    def delete_sale(self, sale_id: int) -> None:
        if self.sales.delete_one({"id": sale_id}).deleted_count == 0:
            raise SaleNotFound(sale_id)
