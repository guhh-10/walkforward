"""Scenario bounds from the selected model's backtest residuals.

One methodology: baseline = the point forecast; the optimistic and conservative
values are baseline plus the 10th and 90th percentile of the horizon-1 residuals
(actual - forecast), i.e. an approximate 80% prediction interval. With fewer than
8 residuals quantiles are meaningless, so a t-distribution approximation on the
residual standard deviation is used instead. No percentage multipliers anywhere.
"""

import math
import statistics
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

Reliability = Literal["low", "medium", "high"]
Method = Literal["empirical_quantile", "t_approximation"]

EMPIRICAL_MIN_RESIDUALS = 8
HIGH_RELIABILITY_MIN_RESIDUALS = 30
LOWER_QUANTILE = 0.10
UPPER_QUANTILE = 0.90

# One-sided 90% critical values of Student's t, by degrees of freedom (n - 1).
# Only df 1..6 are needed: the t path is used for 2..7 residuals.
T_90: dict[int, float] = {
    1: 3.077684,
    2: 1.885618,
    3: 1.637744,
    4: 1.533206,
    5: 1.475884,
    6: 1.439756,
}


@dataclass(frozen=True)
class Scenario:
    optimistic: float  # lower expenditure
    baseline: float
    conservative: float  # higher expenditure
    reliability: Reliability
    method: Method
    n_residuals: int


def reliability_label(n_residuals: int) -> Reliability:
    if n_residuals >= HIGH_RELIABILITY_MIN_RESIDUALS:
        return "high"
    if n_residuals >= EMPIRICAL_MIN_RESIDUALS:
        return "medium"
    return "low"


def _quantile(ordered: Sequence[float], q: float) -> float:
    """Linear-interpolation quantile of an already sorted sequence."""
    position = q * (len(ordered) - 1)
    lower = math.floor(position)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def scenario_bounds(baseline: float, residuals: Sequence[float]) -> Scenario:
    """Optimistic <= baseline <= conservative, all >= 0, by construction."""
    n = len(residuals)
    if n < 2:
        raise ValueError("at least 2 residuals are needed to build scenario bounds")

    baseline = max(0.0, baseline)
    if n >= EMPIRICAL_MIN_RESIDUALS:
        ordered = sorted(residuals)
        low = _quantile(ordered, LOWER_QUANTILE)
        high = _quantile(ordered, UPPER_QUANTILE)
        method: Method = "empirical_quantile"
    else:
        spread = T_90[n - 1] * statistics.stdev(residuals)
        low, high = -spread, spread
        method = "t_approximation"

    # If the model was consistently too high or too low, a quantile can fall on the
    # wrong side of zero; widen the band so that it always contains the baseline.
    low = min(low, 0.0)
    high = max(high, 0.0)
    return Scenario(
        optimistic=max(0.0, baseline + low),
        baseline=baseline,
        conservative=baseline + high,
        reliability=reliability_label(n),
        method=method,
        n_residuals=n,
    )
