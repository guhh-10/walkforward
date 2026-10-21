import datetime as dt
from collections.abc import Iterable
from typing import cast

from sqlalchemy.orm import Session

from app.repositories import summary_repository
from app.repositories.summary_repository import CategoryTotal, MonthTypeTotal
from app.schemas.category import CategoryType
from app.schemas.summary import CategoryBreakdown, MonthlySummary, TrendPoint


# ---------- pure helpers (no DB) ----------
def month_bounds(month: str) -> tuple[dt.date, dt.date]:
    """'2026-10' -> (2026-10-01, 2026-11-01); the end bound is exclusive."""
    year_s, month_s = month.split("-")
    year, mon = int(year_s), int(month_s)
    start = dt.date(year, mon, 1)
    end = dt.date(year + 1, 1, 1) if mon == 12 else dt.date(year, mon + 1, 1)
    return start, end


def months_ending_at(today: dt.date, n: int) -> list[str]:
    """The n calendar months ending at today's month, oldest first."""
    year, mon = today.year, today.month
    months: list[str] = []
    for _ in range(n):
        months.append(f"{year:04d}-{mon:02d}")
        mon -= 1
        if mon == 0:
            mon, year = 12, year - 1
    return months[::-1]


def _major(cents: int) -> float:
    return cents / 100


def build_monthly_summary(month: str, rows: Iterable[CategoryTotal]) -> MonthlySummary:
    items = list(rows)
    type_totals = {"income": 0, "expense": 0}
    for row in items:
        type_totals[row.type] += row.total_cents

    breakdown = [
        CategoryBreakdown(
            category_id=row.category_id,
            name=row.name,
            type=cast(CategoryType, row.type),
            total=_major(row.total_cents),
            pct=round(row.total_cents / type_totals[row.type] * 100, 2),
        )
        for row in sorted(
            items, key=lambda r: (r.type != "income", -r.total_cents, r.name)
        )
    ]
    income, expense = type_totals["income"], type_totals["expense"]
    return MonthlySummary(
        month=month,
        income=_major(income),
        expense=_major(expense),
        net=_major(income - expense),
        by_category=breakdown,
    )


def build_trends(months: list[str], rows: Iterable[MonthTypeTotal]) -> list[TrendPoint]:
    """One point per requested month; months without transactions are zeros."""
    sums: dict[tuple[str, str], int] = {(r.month, r.type): r.total_cents for r in rows}
    points: list[TrendPoint] = []
    for month in months:
        income = sums.get((month, "income"), 0)
        expense = sums.get((month, "expense"), 0)
        points.append(
            TrendPoint(
                month=month,
                income=_major(income),
                expense=_major(expense),
                net=_major(income - expense),
            )
        )
    return points


# ---------- DB-backed entry points ----------
def monthly_summary(db: Session, month: str) -> MonthlySummary:
    start, end = month_bounds(month)
    return build_monthly_summary(
        month, summary_repository.category_totals(db, start, end)
    )


def trends(db: Session, months: int, today: dt.date) -> list[TrendPoint]:
    labels = months_ending_at(today, months)
    start, _ = month_bounds(labels[0])
    _, end = month_bounds(labels[-1])
    return build_trends(labels, summary_repository.month_type_totals(db, start, end))
