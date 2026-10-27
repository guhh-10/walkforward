from collections.abc import Sequence

import pytest
from app.ml import classifier
from app.ml.classifier import InsufficientDataError, evaluate, split_dataset
from app.ml.preprocessing import LabeledDataset

NAMES = {1: "Transport", 2: "Groceries", 3: "Salary", 4: "Unused"}
GROUPS = {1: "expense", 2: "expense", 3: "income", 4: "income"}


class StubModel:
    """A fake classifier: predicts the class named in the text ('pred-<id>')."""

    classes_: Sequence[int] = (1, 2, 3, 4)

    def fit(self, X: Sequence[str], y: Sequence[int]) -> object:
        return self

    def predict_proba(self, X: Sequence[str]) -> Sequence[Sequence[float]]:
        out: list[list[float]] = []
        for text in X:
            wanted = int(text.split("-")[1])
            out.append([0.9 if c == wanted else 0.1 / 3 for c in self.classes_])
        return out


def dataset(spec: list[tuple[str, int]]) -> LabeledDataset:
    return LabeledDataset(
        texts=tuple(t for t, _ in spec),
        labels=tuple(label for _, label in spec),
        groups=tuple(GROUPS[label] for _, label in spec),
    )


# ---------- evaluate ----------
def toy_report() -> classifier.EvaluationReport:
    # actual:    1  1  2  2  3  3
    # predicted: 1  1  2  1  3  3
    spec = [
        ("pred-1", 1),
        ("pred-1", 1),
        ("pred-2", 2),
        ("pred-1", 2),  # actual 2, predicted 1
        ("pred-3", 3),
        ("pred-3", 3),
    ]
    return evaluate(
        StubModel(), dataset(spec), NAMES, GROUPS, n_train=20, test_size=0.2, seed=42
    )


def test_macro_f1_correct_on_toy_data() -> None:
    # class 1: P=2/3 R=1 F1=0.8 | class 2: P=1 R=0.5 F1=2/3 | class 3: P=1 R=1 F1=1
    report = toy_report()
    assert report.accuracy == pytest.approx(5 / 6)
    assert report.macro_f1 == pytest.approx((0.8 + 2 / 3 + 1) / 3)
    assert report.weighted_f1 == pytest.approx((0.8 + 2 / 3 + 1) / 3)  # equal support


def test_eval_report_contains_all_classes_and_supports() -> None:
    report = toy_report()
    by_name = {c.name: c for c in report.per_class}
    assert set(by_name) == set(NAMES.values())  # includes the class with no test data
    assert {n: c.support for n, c in by_name.items()} == {
        "Transport": 2,
        "Groceries": 2,
        "Salary": 2,
        "Unused": 0,
    }
    assert by_name["Groceries"].recall == pytest.approx(0.5)
    assert by_name["Unused"].f1 is None  # undefined without examples
    assert any("Unused" in w for w in report.warnings)


def test_confusion_matrix_rows_are_actual_and_columns_predicted() -> None:
    report = toy_report()
    assert report.confusion_labels == ("Transport", "Groceries", "Salary", "Unused")
    assert report.confusion_matrix == (
        (2, 0, 0, 0),  # actual Transport
        (1, 1, 0, 0),  # actual Groceries: one predicted as Transport
        (0, 0, 2, 0),  # actual Salary
        (0, 0, 0, 0),
    )


def test_low_recall_warning_needs_enough_support() -> None:
    spec = [("pred-2", 1)] * 5 + [("pred-2", 2)] * 5  # class 1: recall 0, support 5
    report = evaluate(
        StubModel(), dataset(spec), NAMES, GROUPS, n_train=20, test_size=0.2, seed=1
    )
    assert any("Low recall" in w and "Transport" in w for w in report.warnings)

    few = [("pred-2", 1)] * 2 + [("pred-2", 2)] * 5  # support 2 < 5: no warning
    report = evaluate(
        StubModel(), dataset(few), NAMES, GROUPS, n_train=20, test_size=0.2, seed=1
    )
    assert not any("Low recall" in w for w in report.warnings)


def test_small_test_set_is_flagged() -> None:
    assert any("high variance" in w for w in toy_report().warnings)


def test_predictions_are_limited_to_the_examples_own_type() -> None:
    # The stub favours class 3 (income) but the example is an expense, so the
    # best expense class (1 or 2, equal) must be chosen, never the income class.
    spec = [("pred-3", 1)]
    report = evaluate(
        StubModel(), dataset(spec), NAMES, GROUPS, n_train=5, test_size=0.2, seed=1
    )
    assert report.confusion_matrix[2][2] == 0
    assert report.confusion_matrix[0][2] == 0
    assert sum(report.confusion_matrix[0]) == 1


def test_report_serialises_to_plain_json_types() -> None:
    data = toy_report().to_dict()
    assert set(data) >= {"accuracy", "macro_f1", "weighted_f1", "per_class"}
    assert data["confusion_matrix"]["labels"][0] == "Transport"
    assert data["per_class"][0]["category_id"] == 1


# ---------- split ----------
def balanced(
    n_per_class: int = 5, classes: Sequence[int] = (1, 2, 3)
) -> LabeledDataset:
    spec = [(f"text {c} {i}", c) for c in classes for i in range(n_per_class)]
    return dataset(spec)


def test_split_is_stratified_and_disjoint() -> None:
    ds = balanced(10)
    split = split_dataset(ds, 0.2, seed=42)
    assert len(split.train) + len(split.test) == len(ds)
    assert set(split.train.texts).isdisjoint(split.test.texts)
    assert sorted(split.test.labels) == [1] * 2 + [2] * 2 + [3] * 2  # 2 per class


def test_split_is_reproducible_for_a_fixed_seed() -> None:
    ds = balanced(10)
    a, b = split_dataset(ds, 0.2, 42), split_dataset(ds, 0.2, 42)
    assert a.test.texts == b.test.texts
    assert a.test.texts != split_dataset(ds, 0.2, 7).test.texts


def test_classes_with_a_single_example_go_to_training_only() -> None:
    ds = dataset([(f"a {i}", 1) for i in range(6)] + [(f"b {i}", 2) for i in range(6)])
    ds = LabeledDataset(
        texts=(*ds.texts, "lonely"),
        labels=(*ds.labels, 3),
        groups=(*ds.groups, "income"),
    )
    split = split_dataset(ds, 0.2, 42)
    assert "lonely" in split.train.texts
    assert 3 not in split.test.labels
    assert split.train_only_labels == (3,)


def test_too_little_data_is_rejected_with_a_clear_error() -> None:
    with pytest.raises(InsufficientDataError, match="at least"):
        split_dataset(balanced(2), 0.2)  # 6 examples
    with pytest.raises(InsufficientDataError, match="two categories"):
        split_dataset(balanced(12, classes=(1,)), 0.2)
    singles = dataset([(f"x {i}", i % 4 + 1) for i in range(4)])
    singles = LabeledDataset(
        texts=singles.texts * 3, labels=singles.labels * 3, groups=singles.groups * 3
    )
    split_dataset(singles, 0.2)  # 12 examples, 3 per class: enough


def test_invalid_test_size() -> None:
    for bad in (0.0, 1.0, -0.1, 2):
        with pytest.raises(ValueError):
            split_dataset(balanced(10), bad)


# ---------- end to end on real text ----------
def test_train_and_evaluate_with_real_pipelines() -> None:
    texts = {
        1: [
            "gojek ride",
            "grab car",
            "taxi airport",
            "bus ticket",
            "grab bike",
            "train",
        ],
        2: [
            "indomaret",
            "alfamart snacks",
            "supermarket",
            "market fruit",
            "belanja",
            "fruit",
        ],
        3: [
            "monthly salary",
            "payroll",
            "gaji bulanan",
            "salary payment",
            "gaji",
            "pay",
        ],
    }
    ds = dataset([(t, label) for label, items in texts.items() for t in items])
    for algorithm in classifier.ALGORITHMS:
        trained = classifier.train_and_evaluate(ds, algorithm, NAMES, GROUPS)
        report = trained.report
        assert 0.0 <= report.accuracy <= 1.0
        assert report.n_train + report.n_test == len(ds)
        assert sum(c.support for c in report.per_class) == report.n_test
