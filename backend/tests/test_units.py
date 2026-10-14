import re

import pytest

from services.inventory_service import (InvalidQuery, build_match, build_pipeline, stock_status,
                                        total_units)


def test_total_units_ignores_bad_values():
    assert total_units({"A": 3, "B": 4}) == 7
    assert total_units({"A": 3, "B": None, "C": "x", "D": True}) == 3
    assert total_units(None) == 0


@pytest.mark.parametrize("total,expected", [(0, "out_of_stock"), (1, "low_stock"), (10, "low_stock"),
                                            (11, "in_stock")])
def test_stock_status_thresholds(total, expected):
    assert stock_status(total, 10) == expected


def test_search_text_is_escaped_literal():
    match = build_match(".*(a|b)", None, None)
    pattern = match["$and"][0]["$or"][0]["name"]["$regex"]
    assert pattern == re.escape(".*(a|b)")


def test_filters_are_exact_matches():
    assert build_match(None, "Sarees", "Women") == {"$and": [{"category": "Sarees"}, {"department": "Women"}]}
    assert build_match(None, None, None) == {}


def test_unknown_sort_field_rejected():
    with pytest.raises(InvalidQuery):
        build_pipeline(10, sort="$where")


def test_status_filter_added_to_pipeline():
    stages = build_pipeline(10, status="low_stock")
    assert {"$match": {"stockStatus": "low_stock"}} in stages
