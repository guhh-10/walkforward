import random

import pytest
from app.ml.backtesting import select_best, walk_forward
from app.ml.forecasting import (
    candidate_models,
    moving_average,
    naive,
    simple_exp_smoothing,
)


def noisy_level(n: int = 36, level: float = 1000.0, sd: float = 100.0) -> list[float]:
    rng = random.Random(42)
    return [level + rng.gauss(0, sd) for _ in range(n)]


# ---------- candidate forecasters ----------
def test_naive_repeats_the_last_month() -> None:
    assert naive([5.0, 7.0, 9.0]) == 9.0
    with pytest.raises(ValueError):
        naive([])


def test_moving_average_uses_the_last_k_or_what_exists() -> None:
    ma3 = moving_average(3)
    assert ma3([1.0, 2.0, 3.0, 10.0]) == pytest.approx(5.0)  # mean of 2, 3, 10
    assert ma3([4.0, 6.0]) == pytest.approx(5.0)  # fewer than 3 months so far
    with pytest.raises(ValueError):
        ma3([])
    with pytest.raises(ValueError):
        moving_average(0)


def test_ses_of_a_constant_series_is_that_constant() -> None:
    assert simple_exp_smoothing([700.0] * 8) == pytest.approx(700.0)


def test_ses_with_one_observation_returns_it() -> None:
    assert simple_exp_smoothing([123.0]) == 123.0
    with pytest.raises(ValueError):
        simple_exp_smoothing([])


def test_ses_tracks_a_step_change_without_lag() -> None:
    """A step is fitted with alpha at its upper bound, so SES collapses to naive.

    statsmodels minimises the in-sample one-step SSE, and on a pure step that is
    achieved by tracking immediately (alpha = 1). The pre-step months cost
    nothing, so nothing pulls alpha back down.
    """
    series = [100.0] * 6 + [200.0] * 6
    assert simple_exp_smoothing(series) == pytest.approx(naive(series))


def test_ses_is_deterministic() -> None:
    series = noisy_level(20)
    assert simple_exp_smoothing(series) == simple_exp_smoothing(series)


# ---------- candidate set ----------
def test_candidate_set_depends_on_history_length() -> None:
    assert list(candidate_models(3)) == ["naive", "ma3"]
    assert list(candidate_models(5)) == ["naive", "ma3"]
    assert list(candidate_models(6)) == ["naive", "ma3", "ses"]


# ---------- behaviour on synthetic data ----------
def test_ses_and_ma_beat_naive_on_noisy_level_data() -> None:
    report = walk_forward(
        noisy_level(), candidate_models(36), min_train=1, min_origins=2
    )
    naive_mae = report.models["naive"].metrics.mae
    assert report.models["ses"].metrics.mae < naive_mae
    assert report.models["ma3"].metrics.mae < naive_mae
    assert select_best(report) in {"ses", "ma3"}


def test_backtest_works_from_a_single_training_month() -> None:
    report = walk_forward(
        [100.0, 110.0, 105.0], candidate_models(3), min_train=1, min_origins=2
    )
    assert report.n_origins == 2
    assert set(report.models) == {"naive", "ma3"}
