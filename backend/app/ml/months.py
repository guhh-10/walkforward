"""Calendar-month helpers for the ML layer. Pure: no database, no framework."""

import datetime as dt


def parse_month(month: str) -> tuple[int, int]:
    """'2026-10' -> (2026, 10)."""
    year_s, mon_s = month.split("-")
    year, mon = int(year_s), int(mon_s)
    if not 1 <= mon <= 12:
        raise ValueError(f"Invalid month: {month!r}")
    return year, mon


def month_index(month: str) -> int:
    """Months since year 0, so that consecutive months differ by exactly 1."""
    year, mon = parse_month(month)
    return year * 12 + (mon - 1)


def month_from_index(index: int) -> str:
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


def month_of(day: dt.date) -> str:
    return f"{day.year:04d}-{day.month:02d}"


def next_month(month: str) -> str:
    return month_from_index(month_index(month) + 1)


def month_range(start: str, end: str) -> list[str]:
    """Every month from start to end inclusive; empty when start is after end."""
    return [
        month_from_index(i) for i in range(month_index(start), month_index(end) + 1)
    ]


def last_complete_month(today: dt.date) -> str:
    """The calendar month before today's month (today's month is still in progress)."""
    return month_from_index(month_index(month_of(today)) - 1)
