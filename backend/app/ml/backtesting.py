"""Walk-forward backtesting (horizon 1) and forecast error metrics.

Pure functions only. At each origin the forecaster sees the history up to the
origin and predicts the next month; it never sees the month it is predicting.
"""

import math
import statistics
import warnings
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from app.ml.forecasting import Forecaster

MIN_ORIGINS = 6
DEFAULT_MIN_TRAIN = 3
ZERO_EPS = 1e-9


class InsufficientHistoryError(ValueError):
    """The series is too short for a meaningful walk-forward backtest."""


# ---------- metrics ----------
@dataclass(frozen=True)
class Metrics:
    mae: float
    rmse: float
    mape: float | None  # percent; None when every actual was (near) zero
    mape_excluded: int  # months left out of MAPE because the actual was ~0


def mae(actuals: Sequence[float], forecasts: Sequence[float]) -> float:
    _check_pairs(actuals, forecasts)
    return statistics.fmean(abs(a - f) for a, f in zip(actuals, forecasts, strict=True))


def rmse(actuals: Sequence[float], forecasts: Sequence[float]) -> float:
    _check_pairs(actuals, forecasts)
    squared = ((a - f) ** 2 for a, f in zip(actuals, forecasts, strict=True))
    return math.sqrt(statistics.fmean(squared))


def mape(
    actuals: Sequence[float], forecasts: Sequence[float], eps: float = ZERO_EPS
) -> tuple[float | None, int]:
    """Mean absolute percentage error, skipping months whose actual is ~0.

    Returns (mape in percent or None, number of excluded months).
    """
    _check_pairs(actuals, forecasts)
    errors = [
        abs(a - f) / abs(a)
        for a, f in zip(actuals, forecasts, strict=True)
        if abs(a) > eps
    ]
    excluded = len(actuals) - len(errors)
    return (statistics.fmean(errors) * 100 if errors else None), excluded


def compute_metrics(actuals: Sequence[float], forecasts: Sequence[float]) -> Metrics:
    mape_value, excluded = mape(actuals, forecasts)
    return Metrics(
        mae=mae(actuals, forecasts),
        rmse=rmse(actuals, forecasts),
        mape=mape_value,
        mape_excluded=excluded,
    )


def _check_pairs(actuals: Sequence[float], forecasts: Sequence[float]) -> None:
    if len(actuals) != len(forecasts):
        raise ValueError("actuals and forecasts must have the same length")
    if not actuals:
        raise ValueError("at least one actual/forecast pair is required")


# ---------- walk-forward harness ----------
@dataclass(frozen=True)
class ModelBacktest:
    name: str
    forecasts: tuple[float, ...]
    actuals: tuple[float, ...]
    residuals: tuple[float, ...]  # actual - forecast, one per origin
    metrics: Metrics
    warnings: tuple[str, ...]  # warnings raised while fitting, de-duplicated


@dataclass(frozen=True)
class BacktestReport:
    n_origins: int
    min_train: int
    models: dict[str, ModelBacktest]


def walk_forward(
    series: Sequence[float],
    forecasters: Mapping[str, Forecaster],
    *,
    min_train: int = DEFAULT_MIN_TRAIN,
    min_origins: int = MIN_ORIGINS,
) -> BacktestReport:
    """Backtest every forecaster with an expanding window and horizon 1.

    For each target index t from `min_train` to the end, each forecaster is
    called with series[:t] only and its forecast is compared with series[t].
    There are therefore `len(series) - min_train` origins.
    """
    if min_train < 1:
        raise ValueError("min_train must be at least 1")
    if not forecasters:
        raise ValueError("at least one forecaster is required")

    n_origins = len(series) - min_train
    if n_origins < min_origins:
        raise InsufficientHistoryError(
            f"Need at least {min_train + min_origins} observations for "
            f"{min_origins} backtest origins; got {len(series)}."
        )

    actuals = tuple(float(v) for v in series[min_train:])
    results: dict[str, ModelBacktest] = {}
    for name, forecaster in forecasters.items():
        forecasts: list[float] = []
        seen: dict[str, None] = {}  # ordered set of warning messages
        for t in range(min_train, len(series)):
            history = tuple(float(v) for v in series[:t])  # immutable: no peeking
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                value = float(forecaster(history))
            for warning in caught:
                seen.setdefault(str(warning.message))
            if not math.isfinite(value):
                raise ValueError(f"Forecaster {name!r} returned a non-finite value")
            forecasts.append(value)

        residuals = tuple(a - f for a, f in zip(actuals, forecasts, strict=True))
        results[name] = ModelBacktest(
            name=name,
            forecasts=tuple(forecasts),
            actuals=actuals,
            residuals=residuals,
            metrics=compute_metrics(actuals, forecasts),
            warnings=tuple(seen),
        )
    return BacktestReport(n_origins=n_origins, min_train=min_train, models=results)


def select_best(report: BacktestReport) -> str:
    """Lowest MAE wins; ties break on RMSE, then on the order the models were given."""
    ranked = sorted(
        enumerate(report.models.values()),
        key=lambda item: (item[1].metrics.mae, item[1].metrics.rmse, item[0]),
    )
    return ranked[0][1].name
