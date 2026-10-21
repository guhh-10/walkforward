import datetime as dt

from app.repositories.summary_repository import CategoryTotal, MonthTypeTotal
from app.services import summary_service


def test_month_bounds_regular_and_december_rollover() -> None:
    assert summary_service.month_bounds("2026-10") == (
        dt.date(2026, 10, 1),
        dt.date(2026, 11, 1),
    )
    assert summary_service.month_bounds("2026-12") == (
        dt.date(2026, 12, 1),
        dt.date(2027, 1, 1),
    )


def test_months_ending_at_crosses_year_boundary() -> None:
    result = summary_service.months_ending_at(dt.date(2026, 2, 15), 4)
    assert result == ["2025-11", "2025-12", "2026-01", "2026-02"]


def test_monthly_summary_totals_net_and_percentages() -> None:
    rows = [
        CategoryTotal(1, "Salary", "income", 500_000),
        CategoryTotal(2, "Groceries", "expense", 30_000),
        CategoryTotal(3, "Housing", "expense", 90_000),
    ]
    s = summary_service.build_monthly_summary("2026-10", rows)
    assert (s.income, s.expense, s.net) == (5000.0, 1200.0, 3800.0)
    # Within a type, largest category first; pct is the share of that type's total.
    assert [c.name for c in s.by_category] == ["Salary", "Housing", "Groceries"]
    pct = {c.name: c.pct for c in s.by_category}
    assert pct == {"Salary": 100.0, "Housing": 75.0, "Groceries": 25.0}


def test_monthly_summary_empty() -> None:
    s = summary_service.build_monthly_summary("2026-10", [])
    assert (s.income, s.expense, s.net, s.by_category) == (0.0, 0.0, 0.0, [])


def test_net_can_be_negative() -> None:
    rows = [CategoryTotal(2, "Groceries", "expense", 1_000)]
    assert summary_service.build_monthly_summary("2026-10", rows).net == -10.0


def test_trends_zero_fill_missing_months_and_types() -> None:
    months = ["2026-08", "2026-09", "2026-10"]
    rows = [
        MonthTypeTotal("2026-08", "expense", 2_000),
        MonthTypeTotal("2026-10", "income", 10_000),
        MonthTypeTotal("2026-10", "expense", 4_000),
    ]
    points = summary_service.build_trends(months, rows)
    assert [p.month for p in points] == months
    assert [(p.income, p.expense, p.net) for p in points] == [
        (0.0, 20.0, -20.0),
        (0.0, 0.0, 0.0),
        (100.0, 40.0, 60.0),
    ]
