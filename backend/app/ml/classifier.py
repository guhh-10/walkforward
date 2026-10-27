"""Category classifier: pipeline definition, prediction, and artifact I/O.

The whole text path (cleaning, TF-IDF, classifier) lives in one sklearn Pipeline,
so train/serve skew is impossible. Class labels are category ids.
"""

import warnings
from collections import Counter
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Literal, Protocol, cast

import joblib
from sklearn import metrics as _metrics
from sklearn import model_selection as _model_selection
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import ComplementNB
from sklearn.pipeline import FeatureUnion, Pipeline

from app.ml.preprocessing import LabeledDataset, clean_text

# joblib ships no type information; keep the untyped surface in one place.
_joblib: Any = joblib
metrics: Any = _metrics
model_selection: Any = _model_selection

ALGORITHMS = ("logreg_tfidf", "complement_nb")
DEFAULT_SEED = 42
DEFAULT_TEST_SIZE = 0.2
MIN_SAMPLES = 10
LOW_RECALL = 0.3
LOW_RECALL_MIN_SUPPORT = 5
SMALL_TEST_SET = 30


class TextClassifier(Protocol):
    """The slice of the sklearn Pipeline API the application relies on."""

    @property
    def classes_(self) -> Sequence[int]: ...

    def fit(self, X: Sequence[str], y: Sequence[int]) -> object: ...

    def predict_proba(self, X: Sequence[str]) -> Sequence[Sequence[float]]: ...


@dataclass(frozen=True)
class Prediction:
    label: int  # category id
    confidence: float  # probability of the label, 0-1


def _vectorizer(
    analyzer: Literal["word", "char_wb"], ngram_range: tuple[int, int]
) -> Any:
    # Typed as Any: some scikit-learn releases ship hints that reject a
    # TfidfVectorizer inside a FeatureUnion even though it is a valid transformer.
    return TfidfVectorizer(
        preprocessor=clean_text,
        analyzer=analyzer,
        ngram_range=ngram_range,
        sublinear_tf=True,
    )


def build_pipeline(algorithm: str, seed: int = DEFAULT_SEED) -> TextClassifier:
    """Unfitted pipeline: word 1-2 grams + char 3-5 grams, sublinear TF-IDF."""
    features: Any = FeatureUnion(
        [
            ("word", _vectorizer("word", (1, 2))),
            ("char", _vectorizer("char_wb", (3, 5))),
        ]
    )
    if algorithm == "logreg_tfidf":
        estimator: Any = LogisticRegression(max_iter=1000, random_state=seed)
    elif algorithm == "complement_nb":
        estimator = ComplementNB()
    else:
        raise ValueError(
            f"Unknown algorithm {algorithm!r}; expected one of {ALGORITHMS}"
        )
    return cast(TextClassifier, Pipeline([("features", features), ("clf", estimator)]))


def fit_pipeline(
    texts: Sequence[str],
    labels: Sequence[int],
    algorithm: str,
    seed: int = DEFAULT_SEED,
) -> TextClassifier:
    if len(texts) != len(labels):
        raise ValueError("texts and labels must have the same length")
    if len(set(labels)) < 2:
        raise ValueError("at least two distinct categories are needed to train")
    model = build_pipeline(algorithm, seed)
    model.fit(list(texts), list(labels))
    return model


def _best_candidate(
    classes: Sequence[int],
    probabilities: Sequence[float],
    allowed: Collection[int] | None,
) -> Prediction | None:
    """Highest-probability allowed class, with probabilities renormalised over them."""
    candidates = [
        (label, p)
        for label, p in zip(classes, probabilities, strict=True)
        if allowed is None or label in allowed
    ]
    total = sum(p for _, p in candidates)
    if not candidates or total <= 0:
        return None
    label, p = max(candidates, key=lambda item: item[1])
    return Prediction(label=label, confidence=min(1.0, p / total))


def predict(
    model: TextClassifier, text: str, allowed: Collection[int] | None = None
) -> Prediction | None:
    """Most likely class for `text`, restricted to `allowed` labels when given.

    Probabilities of the allowed classes are renormalised to sum to 1, so the
    confidence reflects the choice among the categories that are actually valid
    (e.g. only expense categories for an expense). Returns None when the text
    has no usable tokens or none of the allowed labels is known to the model.
    """
    if not clean_text(text):
        return None
    probabilities = [float(p) for p in model.predict_proba([text])[0]]
    classes = [int(c) for c in model.classes_]
    return _best_candidate(classes, probabilities, allowed)


# ---------- evaluation ----------
class InsufficientDataError(ValueError):
    """Not enough reviewed examples to train and evaluate a classifier."""


@dataclass(frozen=True)
class ClassMetrics:
    label: int
    name: str
    precision: float | None  # None when the class has no test examples
    recall: float | None
    f1: float | None
    support: int


@dataclass(frozen=True)
class EvaluationReport:
    accuracy: float
    macro_f1: float  # headline metric: the classes are imbalanced
    weighted_f1: float
    per_class: tuple[ClassMetrics, ...]  # every class the model knows
    confusion_matrix: tuple[tuple[int, ...], ...]  # rows = actual, columns = predicted
    confusion_labels: tuple[str, ...]  # class names, in matrix order
    n_train: int
    n_test: int
    test_size: float
    seed: int
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "accuracy": self.accuracy,
            "macro_f1": self.macro_f1,
            "weighted_f1": self.weighted_f1,
            "per_class": [
                {
                    "category_id": c.label,
                    "name": c.name,
                    "precision": c.precision,
                    "recall": c.recall,
                    "f1": c.f1,
                    "support": c.support,
                }
                for c in self.per_class
            ],
            "confusion_matrix": {
                "labels": list(self.confusion_labels),
                "matrix": [list(row) for row in self.confusion_matrix],
            },
            "n_train": self.n_train,
            "n_test": self.n_test,
            "test_size": self.test_size,
            "seed": self.seed,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class Split:
    train: LabeledDataset
    test: LabeledDataset
    train_only_labels: tuple[int, ...]  # classes with a single example


def split_dataset(
    dataset: LabeledDataset,
    test_size: float = DEFAULT_TEST_SIZE,
    seed: int = DEFAULT_SEED,
) -> Split:
    """Stratified train/test split.

    A class with a single example cannot be stratified, so it goes to the
    training set only (and is reported as not evaluated).
    """
    if not 0 < test_size < 1:
        raise ValueError("test_size must be between 0 and 1")
    if len(dataset) < MIN_SAMPLES:
        raise InsufficientDataError(
            f"Need at least {MIN_SAMPLES} reviewed transactions with distinct "
            f"descriptions; found {len(dataset)}."
        )

    counts = Counter(dataset.labels)
    splittable = {label for label, count in counts.items() if count >= 2}
    if len(splittable) < 2:
        raise InsufficientDataError(
            "Need at least two categories with two or more reviewed examples each."
        )

    stratified = [i for i, label in enumerate(dataset.labels) if label in splittable]
    singles = [i for i, label in enumerate(dataset.labels) if label not in splittable]
    n_test = max(round(test_size * len(stratified)), len(splittable))
    if len(stratified) - n_test < len(splittable):
        raise InsufficientDataError(
            "Not enough examples per category to hold out a stratified test set."
        )

    train_idx, test_idx = model_selection.train_test_split(
        stratified,
        test_size=n_test,
        stratify=[dataset.labels[i] for i in stratified],
        random_state=seed,
    )
    return Split(
        train=dataset.subset(sorted([*train_idx, *singles])),
        test=dataset.subset(sorted(test_idx)),
        train_only_labels=tuple(sorted({dataset.labels[i] for i in singles})),
    )


def evaluate(
    model: TextClassifier,
    test: LabeledDataset,
    class_names: Mapping[int, str],
    class_groups: Mapping[int, str],
    *,
    n_train: int,
    test_size: float,
    seed: int,
) -> EvaluationReport:
    """Score `model` on `test`, predicting exactly as production does.

    Each example is predicted among the categories of its own type only, so
    cross-type mistakes that production cannot make do not count against the model.
    """
    classes = [int(c) for c in model.classes_]
    probabilities = model.predict_proba(list(test.texts))

    predictions: list[int] = []
    for row, group in zip(probabilities, test.groups, strict=True):
        scores = [float(p) for p in row]
        allowed = {c for c in classes if class_groups.get(c) == group}
        best = _best_candidate(classes, scores, allowed)
        predictions.append(best.label if best else classes[scores.index(max(scores))])

    y_true = list(test.labels)
    precision, recall, f1, support = metrics.precision_recall_fscore_support(
        y_true, predictions, labels=classes, zero_division=0
    )
    names = [class_names.get(label, str(label)) for label in classes]
    per_class = tuple(
        ClassMetrics(
            label=label,
            name=names[i],
            precision=float(precision[i]) if int(support[i]) else None,
            recall=float(recall[i]) if int(support[i]) else None,
            f1=float(f1[i]) if int(support[i]) else None,
            support=int(support[i]),
        )
        for i, label in enumerate(classes)
    )
    matrix = metrics.confusion_matrix(y_true, predictions, labels=classes).tolist()

    notes: list[str] = []
    for c in per_class:
        low = c.recall is not None and c.recall < LOW_RECALL
        if low and c.support >= LOW_RECALL_MIN_SUPPORT:
            notes.append(
                f"Low recall ({c.recall:.2f}) for '{c.name}' (support {c.support})."
            )
    unevaluated = [c.name for c in per_class if c.support == 0]
    if unevaluated:
        notes.append(
            "Not evaluated (no test examples): " + ", ".join(unevaluated) + "."
        )
    if len(test) < SMALL_TEST_SET:
        notes.append(
            f"Only {len(test)} test examples: holdout estimates have high variance."
        )

    return EvaluationReport(
        accuracy=float(metrics.accuracy_score(y_true, predictions)),
        macro_f1=float(
            metrics.f1_score(y_true, predictions, average="macro", zero_division=0)
        ),
        weighted_f1=float(
            metrics.f1_score(y_true, predictions, average="weighted", zero_division=0)
        ),
        per_class=per_class,
        confusion_matrix=tuple(tuple(int(v) for v in row) for row in matrix),
        confusion_labels=tuple(names),
        n_train=n_train,
        n_test=len(test),
        test_size=test_size,
        seed=seed,
        warnings=tuple(notes),
    )


@dataclass(frozen=True)
class TrainedClassifier:
    model: TextClassifier
    report: EvaluationReport


def train_and_evaluate(
    dataset: LabeledDataset,
    algorithm: str,
    class_names: Mapping[int, str],
    class_groups: Mapping[int, str],
    *,
    test_size: float = DEFAULT_TEST_SIZE,
    seed: int = DEFAULT_SEED,
) -> TrainedClassifier:
    """Stratified split, fit on the training part, evaluate on the held-out part."""
    split = split_dataset(dataset, test_size, seed)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        model = fit_pipeline(split.train.texts, split.train.labels, algorithm, seed)
    fit_notes = list(dict.fromkeys(f"Training: {w.message}" for w in caught))

    report = evaluate(
        model,
        split.test,
        class_names,
        class_groups,
        n_train=len(split.train),
        test_size=test_size,
        seed=seed,
    )
    single_names = [
        class_names.get(label, str(label)) for label in split.train_only_labels
    ]
    extra = list(fit_notes)
    if single_names:
        extra.append(
            "Trained on a single example only (not evaluated): "
            + ", ".join(single_names)
            + "."
        )
    return TrainedClassifier(
        model=model, report=replace(report, warnings=(*report.warnings, *extra))
    )


# ---------- artifact I/O ----------
def save_pipeline(model: TextClassifier, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _joblib.dump(model, path)


def load_pipeline(path: Path) -> TextClassifier:
    obj: object = _joblib.load(path)
    if not (hasattr(obj, "predict_proba") and hasattr(obj, "classes_")):
        raise ValueError(f"{path} does not contain a classifier pipeline")
    return cast(TextClassifier, obj)
