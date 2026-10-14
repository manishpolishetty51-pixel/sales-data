from fastapi import APIRouter, Depends, HTTPException, Query, Response

from config import get_settings
from database import get_items_collection, get_suppliers_collection
from schemas import ItemCreate, ItemList, ItemOut, ItemUpdate, Options, Stats, StockStatus
from security import require_api_key
from services.inventory_service import InventoryService

router = APIRouter(prefix="/api/inventory", tags=["inventory"])


def get_service() -> InventoryService:
    return InventoryService(get_items_collection(), get_suppliers_collection(),
                            get_settings().low_stock_threshold)


def parse_id(item_id: str) -> int:
    if not item_id.isascii() or not item_id.isdigit() or len(item_id) > 12:
        raise HTTPException(400, "Invalid item id: expected a positive integer.")
    return int(item_id)


Skip = Query(0, ge=0, le=1_000_000)
Limit = Query(20, ge=1, le=100)
SortBy = Query("name", pattern="^(name|sku|price|cost|category|totalStock)$")
Order = Query("asc", pattern="^(asc|desc)$")
Text = Query(None, max_length=100)


@router.get("", response_model=ItemList)
def list_inventory(q: str | None = Text, category: str | None = Text, department: str | None = Text,
                   status: StockStatus | None = None, sort: str = SortBy, order: str = Order,
                   skip: int = Skip, limit: int = Limit, svc: InventoryService = Depends(get_service)):
    """List items (paginated). Accepts the same search and filter parameters as /search and /filter."""
    return svc.list_items(q=q, category=category, department=department, status=status,
                          sort=sort, order=order, skip=skip, limit=limit)


@router.get("/search", response_model=ItemList)
def search_inventory(q: str = Query(..., min_length=1, max_length=100), sort: str = SortBy,
                     order: str = Order, skip: int = Skip, limit: int = Limit,
                     svc: InventoryService = Depends(get_service)):
    """Case-insensitive keyword search over name, SKU, category, sub-category and colour."""
    return svc.list_items(q=q, sort=sort, order=order, skip=skip, limit=limit)


@router.get("/filter", response_model=ItemList)
def filter_inventory(category: str | None = Text, department: str | None = Text,
                     status: StockStatus | None = None, sort: str = SortBy, order: str = Order,
                     skip: int = Skip, limit: int = Limit, svc: InventoryService = Depends(get_service)):
    """Filter by category, department and derived stock status."""
    return svc.list_items(category=category, department=department, status=status,
                          sort=sort, order=order, skip=skip, limit=limit)


@router.get("/stats", response_model=Stats)
def inventory_stats(svc: InventoryService = Depends(get_service)):
    return svc.stats()


@router.get("/options", response_model=Options)
def inventory_options(svc: InventoryService = Depends(get_service)):
    """Distinct categories, departments, stores and suppliers (used by the UI dropdowns)."""
    return svc.options()


@router.get("/{item_id}", response_model=ItemOut)
def get_item(item_id: str, svc: InventoryService = Depends(get_service)):
    return svc.get_item(parse_id(item_id))


@router.post("", response_model=ItemOut, status_code=201, dependencies=[Depends(require_api_key)])
def create_item(body: ItemCreate, response: Response, svc: InventoryService = Depends(get_service)):
    item = svc.create_item(body.model_dump(exclude_none=True))
    response.headers["Location"] = f"/api/inventory/{item['id']}"
    return item


@router.put("/{item_id}", response_model=ItemOut, dependencies=[Depends(require_api_key)])
def update_item(item_id: str, body: ItemUpdate, svc: InventoryService = Depends(get_service)):
    """Partial update: only fields present in the body change; `stock` merges per store."""
    return svc.update_item(parse_id(item_id), body.model_dump(exclude_unset=True))


@router.delete("/{item_id}", status_code=204, dependencies=[Depends(require_api_key)])
def delete_item(item_id: str, svc: InventoryService = Depends(get_service)):
    svc.delete_item(parse_id(item_id))
    return Response(status_code=204)
