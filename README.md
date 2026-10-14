# Sales Management System

FastAPI + PyMongo backend and a React (Vite) dashboard over the existing MongoDB Atlas
collection `neerus.sales`. No data is mocked; nothing is created or migrated in the database.

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
| `DATABASE_NAME`, `COLLECTION_NAME` | `neerus`, `sales` |
| `CORS_ORIGINS` | Allowed frontend origin(s), comma separated |
| `API_KEY` | Required in the `X-API-Key` header for create/update/delete. Enter it in the sidebar ("Write access key"). If unset or `change_me`, writes are disabled. |

## Discovered schema (`neerus.sales`, 9,523 documents)

| Field | Type | Notes |
|---|---|---|
| `_id`, `id` | int | Same integer (not an ObjectId). |
| `store` | str | 7 stores (Jubilee Hills, Banjara Hills, Gachibowli, Kukatpally, Secunderabad, Madhapur, Hitech City). |
| `staff` | str | Staff member's name. |
| `at` | float | Sale time, epoch **milliseconds**. |
| `payment` | str | `Cash`, `Card` or `UPI`. |
| `items` | list | Line items: `id` (product id), `sku`, `name`, `category`, `qty`, `price`. 1 to 3 per sale in current data. |
| `total` | int | Always equals sum of `qty × price`. |

Derived by the API: `unitCount` (sum of `qty`) and `lineCount`. Statistics (sales count, revenue,
average sale, units sold, breakdown by payment and store) are calculated from the real records.

## API summary

`GET /api/health`, `GET /api/sales` (paginated newest first, `skip`/`limit` max 100, plus `q`, `store`,
`payment`, `staff`, `start`, `end`, `sort`, `order`), `GET /api/sales/search?q=`,
`GET /api/sales/filter`, `GET /api/sales/stats` (optional `start`/`end`), `GET /api/sales/options`,
`GET /api/sales/{id}`, and key-protected `POST /api/sales`, `PUT /api/sales/{id}` (partial),
`DELETE /api/sales/{id}`.

`start` and `end` are epoch milliseconds, inclusive. `total` is never accepted from clients; it is
recalculated from `items` on create and whenever `items` is updated.

Errors: 400 bad id, empty update or reversed date range; 401 bad key; 404 unknown id;
422 validation; 503 database unavailable; 504 database timeout.

## Notes and limits

- Creating, editing or deleting a sale does **not** change inventory stock levels or validate that
  item ids exist in the inventory collection.
- Payment methods are limited to Cash, Card and UPI on writes (the values present in the data).
- The API key is a single shared secret, suitable for a trusted team. For untrusted users, add real
  per-user authentication before exposing write access.
- Use a database user with only the roles it needs (read on all, write on `sales` only).
- For production, build the frontend (`npm run build`), serve `dist/` behind the same origin as the API,
  and set `CORS_ORIGINS` to that origin.
