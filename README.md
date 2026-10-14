# Inventory Management System

FastAPI + PyMongo backend and a React (Vite) dashboard over the existing MongoDB Atlas
collection `neerus.inventory`. No data is mocked; nothing is created or migrated in the database.

## Setup

Requires Python 3.11+ and Node 18+.

```powershell
# 1. Backend (terminal 1)
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env        # then fill in MONGODB_URI and API_KEY
.\.venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000

# 2. Frontend (terminal 2)
cd frontend
npm install
npm run dev                   # http://localhost:5173
```

- API docs (Swagger): http://localhost:8000/docs
- Health check: http://localhost:8000/api/health
- Tests: `cd backend; .\.venv\Scripts\python.exe -m pytest`
- Re-run schema discovery (read-only): `.\.venv\Scripts\python.exe scripts\discover.py`

### Configuration (`backend/.env`, git-ignored)

| Variable | Purpose |
|---|---|
| `MONGODB_URI` | Atlas connection string. Backend only; never sent to the browser. |
| `DATABASE_NAME`, `COLLECTION_NAME` | `neerus`, `inventory` |
| `SUPPLIERS_COLLECTION` | `suppliers` (used to show supplier names) |
| `LOW_STOCK_THRESHOLD` | Total units at or below this are "low stock" (default 10) |
| `CORS_ORIGINS` | Allowed frontend origin(s), comma separated |
| `API_KEY` | Required in the `X-API-Key` header for create/update/delete. Enter it in the sidebar ("Write access key"). If unset or `change_me`, writes are disabled. |

## Discovered schema (`neerus.inventory`, 222 documents)

`_id` and `id` are the same integer (not an ObjectId). Fields: `sku` (unique), `name`, `type`,
`department`, `category`, `subCategory`, `style`, `fabric`, `occasion`, `colour`, `sizes` (string or
null; `size` is always null and ignored), `price`, `cost`, `suppliers` (list of ids into
`suppliers`) and `stock` (units per store: Jubilee Hills, Banjara Hills, Gachibowli, Kukatpally,
Secunderabad, Madhapur, Hitech City).

| App concept | Source |
|---|---|
| Product name / SKU / id | `name` / `sku` / `id` |
| Quantity | derived: sum of `stock` values (per-store breakdown on hover and in the edit form) |
| Stock status | derived: 0 = out of stock, 1..threshold = low stock, otherwise in stock |
| Inventory value | derived: units × `price` (retail) and units × `cost` |
| Supplier | `suppliers` ids resolved to `suppliers.name` |

Assumption: every item has a `stock` object (true for all current documents).

## API summary

`GET /api/health`, `GET /api/inventory` (paginated, `skip`/`limit` max 100, plus `q`, `category`,
`department`, `status`, `sort`, `order`), `GET /api/inventory/search?q=`, `GET /api/inventory/filter`,
`GET /api/inventory/stats`, `GET /api/inventory/options`, `GET /api/inventory/{id}`, and key-protected
`POST /api/inventory`, `PUT /api/inventory/{id}` (partial; stock merges per store),
`DELETE /api/inventory/{id}`.

Errors: 400 bad id/empty update, 401 bad key, 404 unknown id, 409 duplicate SKU, 422 validation,
503 database unavailable, 504 database timeout.

## Notes and limits

- SKU uniqueness is checked in code because the collection has no unique index on `sku`
  (only `_id`). Two simultaneous creates with the same SKU could slip through; add a unique index in
  Atlas if that matters. No index was created.
- Deleting an item does not touch `sales`, `transfers`, `shuffles` or `orders`, which reference items by id.
- The API key is a single shared secret, suitable for a trusted team. For untrusted users, add real
  per-user authentication before exposing write access.
- Use a database user with only the roles it needs (read on all, write on `inventory` only).
- For production, build the frontend (`npm run build`), serve `dist/` behind the same origin as the API,
  and set `CORS_ORIGINS` to that origin.
