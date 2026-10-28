from typing import Literal

from pydantic import BaseModel

Reliability = Literal["low", "medium", "high"]
Method = Literal["empirical_quantile", "t_approximation"]


class ModelMetricsOut(BaseModel):
    mae: float
    rmse: float
    mape: float | None  # percent; None when every backtest actual was zero
    mape_excluded: int  # months left out of MAPE because the actual was zero


class BacktestOut(BaseModel):
    per_model: dict[str, ModelMetricsOut]
    residuals_used: int  # backtest origins, i.e. residuals behind the bounds


class ForecastOut(BaseModel):
    """Amounts are in major units, like every other API response."""

    target_month: str  # YYYY-MM
    selected_model: str
    reliability: Reliability
    method: Method
    optimistic: float
    baseline: float
    conservative: float
    warning: str | None
    history_start: str  # YYYY-MM, the first month of the series
    history_months: int
    backtest: BacktestOut
