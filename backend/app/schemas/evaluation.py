import datetime as dt

from pydantic import BaseModel


class ClassMetricsOut(BaseModel):
    category_id: int
    name: str
    precision: float | None
    recall: float | None
    f1: float | None
    support: int


class ConfusionMatrixOut(BaseModel):
    labels: list[str]
    matrix: list[list[int]]  # rows = actual, columns = predicted


class MetricsOut(BaseModel):
    accuracy: float
    macro_f1: float
    weighted_f1: float
    per_class: list[ClassMetricsOut]
    confusion_matrix: ConfusionMatrixOut
    n_train: int
    n_test: int
    test_size: float
    seed: int
    warnings: list[str]


class EvaluationOut(BaseModel):
    version_tag: str
    algorithm: str
    trained_at: dt.datetime
    dataset_size: int
    metrics: MetricsOut
