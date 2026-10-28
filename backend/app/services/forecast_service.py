"""Forecast orchestration: series -> backtest -> model selection -> scenarios.

Consumes the monthly expense series only; no classification field is read.
"""

import datetime as dt

from sqlalchemy.orm import Session

from app.ml.backtesting import select_best, walk_forward
from app.ml.forecasting import SES_MIN_MONTHS, candidate_models
from app.ml.months import month_of, next_month
from app.ml.scenarios import scenario_bounds
from app.schemas.forecast import BacktestOut, ForecastOut, ModelMetricsOut
from app.services import series_service
from app.services.errors import ConflictError

MIN_MONTHS = 3
BACKTEST_MIN_TRAIN = 1  # every candidate can forecast from a single month
BACKTEST_MIN_ORIGINS = 2  # the t-approximation needs at least two residuals


def _major(cents: float) -> float:
    return round(cents / 100, 2)


def generate_forecast(db: Session, today: dt.date) -> ForecastOut:
    """Forecast the next calendar month's total expenditure.

    History runs to the last complete month; the target is the month after
    today's month. Naive, moving-average and SES forecasts are flat, so the
    point forecast is the same for either horizon.
    """
    series = series_service.expense_series(db, today)
    n_months = len(series)
    if n_months < MIN_MONTHS:
        raise ConflictError(
            "INSUFFICIENT_DATA",
            f"Need at least {MIN_MONTHS} complete months of expense history to "
            f"forecast; found {n_months}. The current month counts once it ends.",
        )

    values = [float(v) for v in series.values]  # cents
    models = candidate_models(n_months)
    report = walk_forward(
        values,
        models,
        min_train=BACKTEST_MIN_TRAIN,
        min_origins=BACKTEST_MIN_ORIGINS,
    )
    best = select_best(report)
    baseline = max(0.0, models[best](tuple(values)))
    scenario = scenario_bounds(baseline, report.models[best].residuals)

    notes: list[str] = []
    if n_months < SES_MIN_MONTHS:
        notes.append(
            f"Only {n_months} months of history: only the naive and moving-average "
            "models were compared, so treat this as a rough guide."
        )
    if scenario.method == "t_approximation":
        notes.append(
            f"Based on only {scenario.n_residuals} backtest errors, the range uses a "
            "t-distribution approximation instead of observed error quantiles."
        )
    notes.extend(report.models[best].warnings)

    return ForecastOut(
        target_month=next_month(month_of(today)),
        selected_model=best,
        reliability=scenario.reliability,
        method=scenario.method,
        optimistic=_major(scenario.optimistic),
        baseline=_major(scenario.baseline),
        conservative=_major(scenario.conservative),
        warning=" ".join(notes) or None,
        history_start=series.months[0],
        history_months=n_months,
        backtest=BacktestOut(
            per_model={
                name: ModelMetricsOut(
                    mae=_major(m.metrics.mae),
                    rmse=_major(m.metrics.rmse),
                    mape=m.metrics.mape,
                    mape_excluded=m.metrics.mape_excluded,
                )
                for name, m in report.models.items()
            },
            residuals_used=scenario.n_residuals,
        ),
    )
