"""Monthly series construction and the simplest candidate forecasters.

Everything here consumes transaction amounts and dates only. No classification
field is read at any point, so classifier errors cannot reach the forecast.
"""

import datetime as dt
import statistics
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from app.ml.months import month_of, month_range

# A forecaster maps the history observed so far to a one-step-ahead forecast.
# It must be stateless: the backtest harness calls it once per origin.
Forecaster = Callable[[Sequence[float]], float]


@dataclass(frozen=True)
class MonthlySeries:
    """Total monthly expenditure in integer cents, one value per consecutive month."""

    months: tuple[str, ...]  # 'YYYY-MM', oldest first, no gaps
    values: tuple[int, ...]

    def __post_init__(self) -> None:
        if len(self.months) != len(self.values):
            raise ValueError("months and values must have the same length")

    def __len__(self) -> int:
        return len(self.values)

    @property
    def anchor_month(self) -> str | None:
        """First month of the series (the logging anchor), or None when empty."""
        return self.months[0] if self.months else None


def build_monthly_series(
    totals: Mapping[str, int], anchor: dt.date, end_month: str
) -> MonthlySeries:
    """Complete the month grid from the logging anchor to `end_month` (inclusive).

    - Months with no logged expenses inside the grid become real zeros.
    - Months before the anchor's month are excluded, not zero-filled.
    - Totals outside the grid (before the anchor, after `end_month`) are ignored.
    - An anchor after `end_month` yields an empty series.
    """
    months = month_range(month_of(anchor), end_month)
    return MonthlySeries(
        months=tuple(months),
        values=tuple(totals.get(month, 0) for month in months),
    )


# ---------- candidate forecasters ----------
def naive(history: Sequence[float]) -> float:
    """Next month equals the last observed month."""
    if not history:
        raise ValueError("naive forecast needs at least one observation")
    return float(history[-1])


def moving_average(k: int) -> Forecaster:
    """Mean of the last k months."""
    if k < 1:
        raise ValueError("k must be at least 1")

    def forecast(history: Sequence[float]) -> float:
        if len(history) < k:
            raise ValueError(f"moving average (k={k}) needs {k} observations")
        return statistics.fmean(history[-k:])

    return forecast
