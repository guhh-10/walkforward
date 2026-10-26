import pickle
from pathlib import Path

import pytest
from app.ml import classifier
from app.ml.classifier import TextClassifier

TEXTS = [
    "gojek ride",
    "grab car",
    "taxi airport",
    "bus ticket",
    "indomaret groceries",
    "alfamart snacks",
    "supermarket vegetables",
    "market fruit",
    "monthly salary",
    "payroll deposit",
    "gaji bulanan",
    "salary payment",
]
# Labels are plain ids: 1 = transport, 2 = groceries, 3 = salary.
LABELS = [1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3]


def trained(algorithm: str) -> TextClassifier:
    return classifier.fit_pipeline(TEXTS, LABELS, algorithm)


@pytest.mark.parametrize("algorithm", classifier.ALGORITHMS)
def test_prediction_returns_a_known_label(algorithm: str) -> None:
    result = classifier.predict(trained(algorithm), "gojek ride to the office")
    assert result is not None
    assert result.label in {1, 2, 3}


@pytest.mark.parametrize("algorithm", classifier.ALGORITHMS)
def test_confidence_is_a_probability(algorithm: str) -> None:
    model = trained(algorithm)
    for text in ("gojek ride", "alfamart", "completely unrelated words here"):
        result = classifier.predict(model, text)
        assert result is not None
        assert 0.0 <= result.confidence <= 1.0


def test_logreg_gets_obvious_examples_right() -> None:
    model = trained("logreg_tfidf")
    transport = classifier.predict(model, "Gojek ride home")
    groceries = classifier.predict(model, "Indomaret groceries")
    assert transport is not None and transport.label == 1
    assert groceries is not None and groceries.label == 2


def test_unknown_description_still_predicts() -> None:
    result = classifier.predict(trained("logreg_tfidf"), "zzzxqv blorp")
    assert result is not None
    assert 0.0 <= result.confidence <= 1.0


def test_allowed_labels_restrict_the_prediction_and_renormalise() -> None:
    model = trained("logreg_tfidf")
    unrestricted = classifier.predict(model, "Gojek ride home")
    restricted = classifier.predict(model, "Gojek ride home", allowed={2, 3})
    assert unrestricted is not None and restricted is not None
    assert unrestricted.label == 1
    assert restricted.label in {2, 3}
    # Renormalised over only two classes, the winner takes at least half.
    assert restricted.confidence >= 0.5


def test_no_usable_text_or_no_overlap_gives_no_prediction() -> None:
    model = trained("logreg_tfidf")
    assert classifier.predict(model, "12345 67890") is None
    assert classifier.predict(model, "   ") is None
    assert classifier.predict(model, "gojek ride", allowed={99}) is None


def test_training_is_reproducible_with_a_fixed_seed() -> None:
    a = classifier.predict(trained("logreg_tfidf"), "alfamart milk")
    b = classifier.predict(trained("logreg_tfidf"), "alfamart milk")
    assert a == b


def test_save_and_load_round_trip(tmp_path: Path) -> None:
    model = trained("complement_nb")
    path = tmp_path / "nested" / "clf.joblib"
    classifier.save_pipeline(model, path)
    loaded = classifier.load_pipeline(path)
    for text in ("gojek ride", "monthly salary", "alfamart snacks"):
        assert classifier.predict(loaded, text) == classifier.predict(model, text)


def test_load_rejects_files_that_are_not_classifiers(tmp_path: Path) -> None:
    path = tmp_path / "other.joblib"
    with path.open("wb") as f:
        pickle.dump({"not": "a model"}, f)
    with pytest.raises(ValueError):
        classifier.load_pipeline(path)


def test_fit_validation() -> None:
    with pytest.raises(ValueError):
        classifier.fit_pipeline(["a", "b"], [1, 1], "logreg_tfidf")  # one class
    with pytest.raises(ValueError):
        classifier.fit_pipeline(["a"], [1, 2], "logreg_tfidf")  # length mismatch
    with pytest.raises(ValueError):
        classifier.build_pipeline("svm")
