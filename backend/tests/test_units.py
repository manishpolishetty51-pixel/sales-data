import re

import pytest

from services.sales_service import InvalidQuery, SalesService, build_match, compute_total, unit_count
from tests.conftest import FakeCollection


def test_compute_total_and_units():
    items = [{"qty": 2, "price": 100}, {"qty": 1, "price": 50}]
    assert compute_total(items) == 250
    assert unit_count([{"qty": 2}, {"qty": 3}, {"qty": None}, {"qty": True}, "bad"]) == 5
    assert unit_count(None) == 0


def test_search_text_is_escaped_literal():
    ors = build_match(q=".*(a|b)")["$and"][0]["$or"]
    assert ors[0]["staff"]["$regex"] == re.escape(".*(a|b)")
    assert all("id" not in o for o in ors)  # non-numeric text never searches by id


def test_numeric_search_also_matches_sale_id():
    assert {"id": 123} in build_match(q="123")["$and"][0]["$or"]


def test_filters_and_date_range():
    m = build_match(store="Madhapur", payment="UPI", staff="Asha", start=10, end=20)
    assert m["$and"] == [{"store": "Madhapur"}, {"payment": "UPI"}, {"staff": "Asha"},
                         {"at": {"$gte": 10, "$lte": 20}}]
    assert build_match() == {}


def test_reversed_date_range_rejected():
    with pytest.raises(InvalidQuery):
        build_match(start=20, end=10)


def test_unknown_sort_field_rejected():
    with pytest.raises(InvalidQuery):
        SalesService(FakeCollection()).list_sales(sort="$where")
