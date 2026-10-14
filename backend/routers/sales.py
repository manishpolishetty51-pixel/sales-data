from fastapi import APIRouter, Depends, HTTPException, Query, Response

from database import get_sales_collection
from schemas import Options, SaleCreate, SaleList, SaleOut, SaleUpdate, Stats
from security import require_api_key
from services.sales_service import SalesService

router = APIRouter(prefix="/api/sales", tags=["sales"])


def get_service() -> SalesService:
    return SalesService(get_sales_collection())


def parse_id(sale_id: str) -> int:
    if not sale_id.isascii() or not sale_id.isdigit() or len(sale_id) > 12:
        raise HTTPException(400, "Invalid sale id: expected a positive integer.")
    return int(sale_id)


Skip = Query(0, ge=0, le=1_000_000)
Limit = Query(20, ge=1, le=100)
SortBy = Query("at", pattern="^(at|total|store|staff|payment|id)$")
Order = Query("desc", pattern="^(asc|desc)$")


def text_param():
    # A fresh Query per parameter: FastAPI binds the parameter name to the object,
    # so sharing one instance would make every text parameter read the same query key.
    return Query(None, max_length=100)


# Date range as epoch milliseconds (e.g. JavaScript Date.getTime()), inclusive.
Start = Query(None, ge=0, description="Only sales at or after this time (epoch ms)")
End = Query(None, ge=0, description="Only sales at or before this time (epoch ms)")


@router.get("", response_model=SaleList)
def list_sales(q: str | None = text_param(), store: str | None = text_param(), payment: str | None = text_param(),
               staff: str | None = text_param(), start: int | None = Start, end: int | None = End,
               sort: str = SortBy, order: str = Order, skip: int = Skip, limit: int = Limit,
               svc: SalesService = Depends(get_service)):
    """List sales (paginated, newest first). Accepts the same parameters as /search and /filter."""
    return svc.list_sales(q=q, store=store, payment=payment, staff=staff, start=start, end=end,
                          sort=sort, order=order, skip=skip, limit=limit)


@router.get("/search", response_model=SaleList)
def search_sales(q: str = Query(..., min_length=1, max_length=100), sort: str = SortBy,
                 order: str = Order, skip: int = Skip, limit: int = Limit,
                 svc: SalesService = Depends(get_service)):
    """Keyword search over sale id, staff, store and line-item name, SKU and category."""
    return svc.list_sales(q=q, sort=sort, order=order, skip=skip, limit=limit)


@router.get("/filter", response_model=SaleList)
def filter_sales(store: str | None = text_param(), payment: str | None = text_param(), staff: str | None = text_param(),
                 start: int | None = Start, end: int | None = End, sort: str = SortBy,
                 order: str = Order, skip: int = Skip, limit: int = Limit,
                 svc: SalesService = Depends(get_service)):
    """Filter by store, payment method, staff member and date range."""
    return svc.list_sales(store=store, payment=payment, staff=staff, start=start, end=end,
                          sort=sort, order=order, skip=skip, limit=limit)


@router.get("/stats", response_model=Stats)
def sales_stats(start: int | None = Start, end: int | None = End,
                svc: SalesService = Depends(get_service)):
    """Totals, average sale, units sold and breakdowns by payment method and store."""
    return svc.stats(start=start, end=end)


@router.get("/options", response_model=Options)
def sales_options(svc: SalesService = Depends(get_service)):
    """Distinct stores, payment methods and staff (used by the UI dropdowns)."""
    return svc.options()


@router.get("/{sale_id}", response_model=SaleOut)
def get_sale(sale_id: str, svc: SalesService = Depends(get_service)):
    return svc.get_sale(parse_id(sale_id))


@router.post("", response_model=SaleOut, status_code=201, dependencies=[Depends(require_api_key)])
def create_sale(body: SaleCreate, response: Response, svc: SalesService = Depends(get_service)):
    sale = svc.create_sale(body.model_dump(exclude_none=True))
    response.headers["Location"] = f"/api/sales/{sale['id']}"
    return sale


@router.put("/{sale_id}", response_model=SaleOut, dependencies=[Depends(require_api_key)])
def update_sale(sale_id: str, body: SaleUpdate, svc: SalesService = Depends(get_service)):
    """Partial update; sending `items` replaces the line items and recalculates the total."""
    return svc.update_sale(parse_id(sale_id), body.model_dump(exclude_unset=True))


@router.delete("/{sale_id}", status_code=204, dependencies=[Depends(require_api_key)])
def delete_sale(sale_id: str, svc: SalesService = Depends(get_service)):
    svc.delete_sale(parse_id(sale_id))
    return Response(status_code=204)
