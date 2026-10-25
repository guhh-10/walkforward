import math

import pytest
from app.ml.backtesting import compute_metrics, mae, mape, rmse


def test_mae_and_rmse_known_answers() -> None:
    actuals = [10.0, 20.0, 30.0]
    forecasts = [12.0, 18.0, 33.0]  # errors: 2, 2, 3
    assert mae(actuals, forecasts) == pytest.approx(7 / 3)
    assert rmse(actuals, forecasts) == pytest.approx(math.sqrt((4 + 4 + 9) / 3))


def test_mape_known_answer() -> None:
    value, excluded = mape([100.0, 200.0], [110.0, 180.0])  # 10% and 10%
    assert value == pytest.approx(10.0)
    assert excluded == 0


def test_mape_skips_zero_actuals_and_counts_them() -> None:
    value, excluded = mape([0.0, 100.0, 0.0, 50.0], [5.0, 90.0, 1.0, 55.0])
    assert value == pytest.approx(10.0)  # only 10% and 10% count
    assert excluded == 2


def test_mape_is_none_when_every_actual_is_zero() -> None:
    value, excluded = mape([0.0, 0.0], [1.0, 2.0])
    assert value is None
    assert excluded == 2


def test_metrics_reject_empty_or_mismatched_input() -> None:
    with pytest.raises(ValueError):
        mae([], [])
    with pytest.raises(ValueError):
        rmse([1.0], [1.0, 2.0])


def test_perfect_forecast_has_zero_error() -> None:
    m = compute_metrics([5.0, 6.0], [5.0, 6.0])
    assert (m.mae, m.rmse, m.mape) == (0.0, 0.0, 0.0)
