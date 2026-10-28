"""Monthly series construction and the simplest candidate forecasters.

Everything here consumes transaction amounts and dates only. No classification
field is read at any point, so classifier errors cannot reach the forecast.
"""

import datetime as dt
import statistics
import warnings
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, cast

import numpy as np
import numpy.typing as npt
from statsmodels.tsa.holtwinters import SimpleExpSmoothing

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
    """Mean of the last k months (of all of them while fewer than k exist)."""
    if k < 1:
        raise ValueError("k must be at least 1")

    def forecast(history: Sequence[float]) -> float:
        if not history:
            raise ValueError("moving average needs at least one observation")
        return statistics.fmean(history[-k:])

    return forecast


def simple_exp_smoothing(history: Sequence[float]) -> float:
    """Simple exponential smoothing fitted with statsmodels.

    statsmodels estimates the smoothing constant and the initial level by
    minimising the in-sample one-step SSE; the returned value is the
    one-step-ahead forecast. On a series with fewer than two observations there
    is nothing to fit, so the single observation is returned as-is.
    """
    if not history:
        raise ValueError("exponential smoothing needs at least one observation")
    if len(history) < 2:
        return float(history[0])
    with warnings.catch_warnings():
        # A perfect in-sample fit (an all-zero or constant history, which
        # zero-filled months produce) makes statsmodels' AIC/BIC divide by zero.
        # Only the forecast is used here, so that warning carries no signal. The
        # guard spans both calls because forecast() re-fits internally.
        warnings.simplefilter("ignore", RuntimeWarning)
        # statsmodels ships no type information, so everything it returns is
        # Unknown to the type checker; the single step forecast below is a float
        # array.
        model: Any = SimpleExpSmoothing(
            np.asarray(history, dtype=float), initialization_method="estimated"
        )
        forecast = cast(npt.NDArray[np.float64], model.fit(optimized=True).forecast(1))
    return float(forecast[0])


# ---------- the fixed core candidate set ----------
SES_MIN_MONTHS = 6


def candidate_models(n_months: int) -> dict[str, Forecaster]:
    """Naive and a 3-month moving average always; SES once there are enough months."""
    models: dict[str, Forecaster] = {"naive": naive, "ma3": moving_average(3)}
    if n_months >= SES_MIN_MONTHS:
        models["ses"] = simple_exp_smoothing
    return models
