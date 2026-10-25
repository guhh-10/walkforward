import datetime as dt

import pytest
from app.ml.months import (
    last_complete_month,
    month_of,
    month_range,
    next_month,
    parse_month,
)


def test_month_range_is_inclusive_and_crosses_year_boundary() -> None:
    assert month_range("2025-11", "2026-02") == [
        "2025-11",
        "2025-12",
        "2026-01",
        "2026-02",
    ]
    assert month_range("2026-05", "2026-05") == ["2026-05"]


def test_month_range_empty_when_start_after_end() -> None:
    assert month_range("2026-06", "2026-05") == []


def test_last_complete_month_is_the_previous_month() -> None:
    assert last_complete_month(dt.date(2026, 10, 22)) == "2026-09"
    assert last_complete_month(dt.date(2026, 1, 1)) == "2025-12"


def test_next_month_and_month_of() -> None:
    assert next_month("2026-12") == "2027-01"
    assert month_of(dt.date(2026, 3, 31)) == "2026-03"


def test_parse_month_rejects_invalid_month() -> None:
    assert parse_month("2026-10") == (2026, 10)
    with pytest.raises(ValueError):
        parse_month("2026-13")
