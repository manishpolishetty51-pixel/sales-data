"""Pydantic models for requests and responses. Field names match the existing MongoDB documents."""
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

StockStatus = Literal["in_stock", "low_stock", "out_of_stock"]

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
Money = Annotated[int, Field(ge=0, le=100_000_000)]
Units = Annotated[int, Field(ge=0, le=1_000_000)]


def _check_store_names(stock: dict[str, int]) -> dict[str, int]:
    for store in stock:
        if not store.strip() or "." in store or store.startswith("$") or len(store) > 60:
            raise ValueError(f"invalid store name: {store!r}")
    return stock


class SupplierRef(BaseModel):
    id: int
    name: str | None = None


class ItemOut(BaseModel):
    id: int
    sku: str | None = None
    name: str | None = None
    type: str | None = None
    department: str | None = None
    category: str | None = None
    subCategory: str | None = None
    style: str | None = None
    fabric: str | None = None
    occasion: str | None = None
    colour: str | None = None
    sizes: str | None = None
    price: int | None = None
    cost: int | None = None
    suppliers: list[SupplierRef] = []
    stock: dict[str, int] = {}
    totalStock: int
    stockStatus: StockStatus


class ItemList(BaseModel):
    items: list[ItemOut]
    total: int
    skip: int
    limit: int


class _ItemWrite(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @field_validator("stock", check_fields=False)
    @classmethod
    def _stock_keys(cls, v):
        return _check_store_names(v)


class ItemCreate(_ItemWrite):
    sku: Text
    name: Text
    category: Text
    department: Text
    price: Money
    cost: Money
    stock: dict[str, Units]
    type: Text | None = None
    subCategory: Text | None = None
    style: Text | None = None
    fabric: Text | None = None
    occasion: Text | None = None
    colour: Text | None = None
    sizes: Text | None = None
    suppliers: list[int] = []


class ItemUpdate(_ItemWrite):
    """Partial update: only the fields you send are changed. `stock` is merged per store."""

    sku: Text = None
    name: Text = None
    category: Text = None
    department: Text = None
    price: Money = None
    cost: Money = None
    stock: dict[str, Units] = None
    type: Text = None
    subCategory: Text = None
    style: Text = None
    fabric: Text = None
    occasion: Text = None
    colour: Text = None
    sizes: Text = None
    suppliers: list[int] = None


class Stats(BaseModel):
    totalItems: int
    totalUnits: int
    lowStockItems: int
    outOfStockItems: int
    inventoryValueRetail: int
    inventoryValueCost: int
    lowStockThreshold: int


class Options(BaseModel):
    categories: list[str]
    departments: list[str]
    stores: list[str]
    suppliers: list[SupplierRef]
    statuses: list[StockStatus]
    lowStockThreshold: int
