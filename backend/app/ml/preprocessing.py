"""Text cleaning for transaction descriptions. Pure and picklable.

`clean_text` is used as the vectorizers' preprocessor inside the sklearn Pipeline,
so training and prediction always clean text the same way.
"""

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

_PUNCTUATION = re.compile(r"[^\w\s]|_")


def clean_text(text: str) -> str:
    """Lowercase, strip punctuation, drop pure-numeric tokens, collapse whitespace.

    >>> clean_text("Gojek*Ride 85000, Jakarta!")
    'gojek ride jakarta'
    """
    without_punctuation = _PUNCTUATION.sub(" ", text.lower())
    tokens = [t for t in without_punctuation.split() if not t.isdigit()]
    return " ".join(tokens)


# ---------- labeled dataset ----------
@dataclass(frozen=True)
class LabeledRow:
    text: str
    label: int  # category id
    group: str  # transaction type ('income' | 'expense'): which labels are valid


@dataclass(frozen=True)
class LabeledDataset:
    texts: tuple[str, ...]
    labels: tuple[int, ...]
    groups: tuple[str, ...]

    def __post_init__(self) -> None:
        if not len(self.texts) == len(self.labels) == len(self.groups):
            raise ValueError("texts, labels and groups must have the same length")

    def __len__(self) -> int:
        return len(self.texts)

    def subset(self, indices: Sequence[int]) -> "LabeledDataset":
        return LabeledDataset(
            texts=tuple(self.texts[i] for i in indices),
            labels=tuple(self.labels[i] for i in indices),
            groups=tuple(self.groups[i] for i in indices),
        )


def build_labeled_dataset(rows: Iterable[LabeledRow]) -> LabeledDataset:
    """One example per distinct cleaned description.

    `rows` must be in chronological order: when the same cleaned description
    appears more than once, the most recent label wins. That resolves conflicting
    labels and keeps identical texts out of both sides of a train/test split.
    Descriptions with no usable tokens are dropped.
    """
    latest: dict[str, LabeledRow] = {}
    for row in rows:
        key = clean_text(row.text)
        if key:
            latest[key] = row
    kept = list(latest.values())
    return LabeledDataset(
        texts=tuple(r.text for r in kept),
        labels=tuple(r.label for r in kept),
        groups=tuple(r.group for r in kept),
    )
