import random
import warnings
from collections.abc import Sequence

import pytest
from app.ml.backtesting import (
    InsufficientHistoryError,
    select_best,
    walk_forward,
)
from app.ml.forecasting import Forecaster, moving_average, naive


def noisy_level(n: int = 36, level: float = 1000.0, sd: float = 100.0) -> list[float]:
    rng = random.Random(42)
    return [level + rng.gauss(0, sd) for _ in range(n)]


# ---------- origins ----------
def test_walk_forward_origin_counts() -> None:
    series = [float(v) for v in range(1, 13)]  # 12 observations
    report = walk_forward(series, {"naive": naive}, min_train=3)
    assert report.n_origins == 9
    model = report.models["naive"]
    assert len(model.forecasts) == len(model.actuals) == len(model.residuals) == 9
    assert model.actuals == tuple(float(v) for v in range(4, 13))


def test_min_origins_enforced() -> None:
    series = [1.0] * 8  # 8 - 3 = 5 origins < 6
    with pytest.raises(InsufficientHistoryError):
        walk_forward(series, {"naive": naive}, min_train=3, min_origins=6)
    # Exactly enough is accepted.
    assert walk_forward([1.0] * 9, {"naive": naive}, min_train=3).n_origins == 6


def test_insufficient_history_is_a_value_error() -> None:
    assert issubclass(InsufficientHistoryError, ValueError)


def test_invalid_arguments() -> None:
    with pytest.raises(ValueError):
        walk_forward([1.0] * 12, {}, min_train=3)
    with pytest.raises(ValueError):
        walk_forward([1.0] * 12, {"naive": naive}, min_train=0)


# ---------- leakage ----------
def test_forecaster_never_sees_the_month_it_predicts() -> None:
    seen: list[tuple[float, ...]] = []

    def spy(history: Sequence[float]) -> float:
        seen.append(tuple(history))
        return history[-1]

    series = [float(v) for v in range(10, 22)]  # 12 values
    walk_forward(series, {"spy": spy}, min_train=3)

    assert [len(h) for h in seen] == list(range(3, 12))
    for history, target in zip(seen, series[3:], strict=True):
        assert target not in history  # values are unique, so no peeking
    assert seen[0] == (10.0, 11.0, 12.0)


# ---------- residuals and metrics ----------
def test_residual_is_actual_minus_forecast() -> None:
    series = [10.0, 10.0, 10.0, 20.0, 20.0, 20.0, 20.0, 20.0, 20.0]
    model = walk_forward(series, {"naive": naive}, min_train=3).models["naive"]
    assert model.forecasts[0] == 10.0
    assert model.residuals[0] == 10.0  # 20 - 10: under-forecast is positive
    assert model.residuals[1] == 0.0


def test_constant_series_has_zero_error() -> None:
    models: dict[str, Forecaster] = {"naive": naive, "ma3": moving_average(3)}
    report = walk_forward([500.0] * 12, models, min_train=3)
    for model in report.models.values():
        assert (model.metrics.mae, model.metrics.rmse, model.metrics.mape) == (0, 0, 0)


def test_mape_excludes_zero_months_in_the_report() -> None:
    series = [100.0, 100.0, 100.0, 0.0, 100.0, 0.0, 100.0, 100.0, 100.0, 100.0]
    metrics = (
        walk_forward(series, {"naive": naive}, min_train=3).models["naive"].metrics
    )
    assert metrics.mape_excluded == 2


def test_moving_average_beats_naive_on_noisy_level_data() -> None:
    models: dict[str, Forecaster] = {"naive": naive, "ma3": moving_average(3)}
    report = walk_forward(noisy_level(), models, min_train=3)
    assert report.models["ma3"].metrics.mae < report.models["naive"].metrics.mae
    assert select_best(report) == "ma3"


# ---------- selection ----------
def test_select_best_prefers_lower_mae() -> None:
    series = [10.0, 20.0] * 6
    report = walk_forward(
        series, {"naive": naive, "ma2": moving_average(2)}, min_train=3
    )
    assert select_best(report) == "ma2"


def test_select_best_breaks_mae_ties_on_rmse() -> None:
    series = [0.0] * 3 + [10.0] * 6  # six origins, every actual is 10

    def steady(history: Sequence[float]) -> float:
        return 8.0  # errors 2, 2, 2, 2, 2, 2

    def spiky(history: Sequence[float]) -> float:
        return 6.0 if len(history) % 2 else 10.0  # errors 4, 0, 4, 0, 4, 0

    models: dict[str, Forecaster] = {"spiky": spiky, "steady": steady}
    report = walk_forward(series, models, min_train=3)
    spiky_m, steady_m = report.models["spiky"].metrics, report.models["steady"].metrics
    assert spiky_m.mae == pytest.approx(steady_m.mae)
    assert spiky_m.rmse > steady_m.rmse
    assert select_best(report) == "steady"  # listed second, wins on RMSE


def test_select_best_full_tie_uses_given_order() -> None:
    report = walk_forward(
        [5.0] * 12, {"first": naive, "second": lambda h: h[-1]}, min_train=3
    )
    assert select_best(report) == "first"


# ---------- warnings and bad output ----------
def test_warnings_from_a_model_are_captured_and_deduplicated() -> None:
    def noisy_model(history: Sequence[float]) -> float:
        warnings.warn("did not converge", RuntimeWarning, stacklevel=2)
        return history[-1]

    models: dict[str, Forecaster] = {"noisy": noisy_model, "quiet": naive}
    report = walk_forward([1.0] * 12, models, min_train=3)
    assert report.models["noisy"].warnings == ("did not converge",)
    assert report.models["quiet"].warnings == ()


def test_non_finite_forecast_is_rejected() -> None:
    def broken(history: Sequence[float]) -> float:
        return float("nan")

    with pytest.raises(ValueError, match="non-finite"):
        walk_forward([1.0] * 12, {"broken": broken}, min_train=3)
