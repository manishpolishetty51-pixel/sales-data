"""Pydantic models for requests and responses. Field names match the existing MongoDB documents."""
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

PaymentMethod = Literal["Cash", "Card", "UPI"]

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
Money = Annotated[int, Field(ge=0, le=100_000_000)]
Quantity = Annotated[int, Field(ge=1, le=10_000)]
Timestamp = Annotated[float, Field(ge=0, le=4_102_444_800_000)]  # milliseconds since epoch


class SaleItemOut(BaseModel):
    id: int | None = None
    sku: str | None = None
    name: str | None = None
    category: str | None = None
    qty: int | None = None
    price: int | None = None


class SaleOut(BaseModel):
    id: int
    store: str | None = None
    staff: str | None = None
    at: float | None = None
    payment: str | None = None
    total: int | None = None
    items: list[SaleItemOut] = []
    unitCount: int
    lineCount: int


class SaleList(BaseModel):
    sales: list[SaleOut]
    total: int
    skip: int
    limit: int


class SaleItemIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: Annotated[int, Field(ge=1, le=10**9)]
    sku: Text
    name: Text
    category: Text
    qty: Quantity
    price: Money


class _SaleWrite(BaseModel):
    # `total` is always computed by the server from the line items, so it is rejected here.
    model_config = ConfigDict(extra="forbid")


class SaleCreate(_SaleWrite):
    store: Text
    staff: Text
    payment: PaymentMethod
    items: Annotated[list[SaleItemIn], Field(min_length=1, max_length=50)]
    at: Timestamp | None = None  # defaults to now


class SaleUpdate(_SaleWrite):
    """Partial update: only the fields you send change. `items` replaces the whole list
    and the total is recalculated."""

    store: Text = None
    staff: Text = None
    payment: PaymentMethod = None
    items: Annotated[list[SaleItemIn], Field(min_length=1, max_length=50)] = None
    at: Timestamp = None


class Breakdown(BaseModel):
    name: str | None
    count: int
    revenue: int


class Stats(BaseModel):
    totalSales: int
    totalRevenue: int
    averageSale: int
    unitsSold: int
    firstSaleAt: float | None
    lastSaleAt: float | None
    byPayment: list[Breakdown]
    byStore: list[Breakdown]


class Options(BaseModel):
    stores: list[str]
    payments: list[str]
    staff: list[str]
