import statistics

import pytest
from app.ml.scenarios import reliability_label, scenario_bounds

# Appendix A of the spec: residuals of the selected model over 10 origins.
APPENDIX = [-40.0, -12.0, 8.0, 15.0, -25.0, 30.0, 5.0, -8.0, 18.0, -20.0]


def test_quantile_bounds_bracket_the_baseline() -> None:
    s = scenario_bounds(820.0, APPENDIX)
    assert s.method == "empirical_quantile"
    assert s.optimistic < s.baseline < s.conservative
    # Linear-interpolation quantiles: Q10 = -26.5, Q90 = +19.2.
    assert s.optimistic == pytest.approx(820 - 26.5)
    assert s.conservative == pytest.approx(820 + 19.2)
    assert s.reliability == "medium"
    assert s.n_residuals == 10


def test_bounds_are_clipped_at_zero() -> None:
    s = scenario_bounds(50.0, [-500.0, -400.0, -300.0, 10.0, 20.0, 30.0, 40.0, 50.0])
    assert s.optimistic == 0.0
    assert s.baseline == 50.0

    t_path = scenario_bounds(10.0, [-100.0, 100.0, -50.0])
    assert t_path.optimistic == 0.0


def test_negative_baseline_is_clipped() -> None:
    s = scenario_bounds(-5.0, [1.0, -1.0, 2.0])
    assert s.baseline == 0.0
    assert 0.0 <= s.optimistic <= s.baseline <= s.conservative


@pytest.mark.parametrize("sign", [1.0, -1.0])
def test_ordering_holds_when_the_model_is_always_wrong_the_same_way(
    sign: float,
) -> None:
    # Every residual has the same sign, so a raw quantile would miss the baseline.
    residuals = [sign * v for v in range(10, 20)]
    s = scenario_bounds(500.0, residuals)
    assert s.optimistic <= s.baseline <= s.conservative


def test_t_approximation_is_used_only_below_eight_residuals() -> None:
    seven = [10.0, -4.0, 6.0, -8.0, 3.0, 0.0, -2.0]
    eight = [*seven, 5.0]
    assert scenario_bounds(100.0, seven).method == "t_approximation"
    assert scenario_bounds(100.0, eight).method == "empirical_quantile"


def test_t_approximation_matches_the_formula() -> None:
    residuals = [4.0, -6.0, 2.0, -1.0, 5.0]  # n = 5, df = 4, t(0.90) = 1.533206
    spread = 1.533206 * statistics.stdev(residuals)
    s = scenario_bounds(200.0, residuals)
    assert s.optimistic == pytest.approx(200.0 - spread)
    assert s.conservative == pytest.approx(200.0 + spread)
    assert s.reliability == "low"


def test_zero_residuals_give_a_zero_width_band() -> None:
    s = scenario_bounds(300.0, [0.0, 0.0, 0.0])
    assert (s.optimistic, s.baseline, s.conservative) == (300.0, 300.0, 300.0)


def test_reliability_labels_follow_the_residual_count() -> None:
    assert [reliability_label(n) for n in (2, 7, 8, 29, 30, 100)] == [
        "low",
        "low",
        "medium",
        "medium",
        "high",
        "high",
    ]


def test_at_least_two_residuals_are_required() -> None:
    with pytest.raises(ValueError):
        scenario_bounds(100.0, [1.0])
    with pytest.raises(ValueError):
        scenario_bounds(100.0, [])
