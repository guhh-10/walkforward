"""Train the category classifier (explicit, manual; never automatic).

Usage (from backend/):
    python -m app.scripts.train_classifier [--algorithm logreg_tfidf|complement_nb]
                                           [--test-size 0.2]
"""

import argparse
import sys
from collections.abc import Sequence

from app.database.connection import SessionLocal
from app.ml.classifier import ALGORITHMS, DEFAULT_TEST_SIZE, InsufficientDataError
from app.services import training_service


def _test_size(value: str) -> float:
    size = float(value)
    if not 0 < size < 1:
        raise argparse.ArgumentTypeError("must be between 0 and 1 (exclusive)")
    return size


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train the category classifier.")
    parser.add_argument("--algorithm", choices=ALGORITHMS, default=ALGORITHMS[0])
    parser.add_argument("--test-size", type=_test_size, default=DEFAULT_TEST_SIZE)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    with SessionLocal() as db:
        try:
            version = training_service.train_new_version(
                db, args.algorithm, args.test_size
            )
        except InsufficientDataError as exc:
            print(f"Training aborted: {exc}", file=sys.stderr)
            return 1

    print(f"Trained {version.version_tag} ({version.algorithm}) and activated it.")
    print(f"  dataset size : {version.dataset_size}")
    print(f"  artifact     : {version.artifact_path}")
    print("  metrics      : Model evaluation page, or GET /api/ml/evaluation/latest")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
