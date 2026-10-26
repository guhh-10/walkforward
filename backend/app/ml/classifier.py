"""Category classifier: pipeline definition, prediction, and artifact I/O.

The whole text path (cleaning, TF-IDF, classifier) lives in one sklearn Pipeline,
so train/serve skew is impossible. Class labels are category ids.
"""

from collections.abc import Collection, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Protocol, cast

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import ComplementNB
from sklearn.pipeline import FeatureUnion, Pipeline

from app.ml.preprocessing import clean_text

# joblib ships no type information; keep the untyped surface in one place.
_joblib: Any = joblib

ALGORITHMS = ("logreg_tfidf", "complement_nb")
DEFAULT_SEED = 42


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


# ---------- artifact I/O ----------
def save_pipeline(model: TextClassifier, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _joblib.dump(model, path)


def load_pipeline(path: Path) -> TextClassifier:
    obj: object = _joblib.load(path)
    if not (hasattr(obj, "predict_proba") and hasattr(obj, "classes_")):
        raise ValueError(f"{path} does not contain a classifier pipeline")
    return cast(TextClassifier, obj)
