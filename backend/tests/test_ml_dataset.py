from app.ml.preprocessing import LabeledRow, build_labeled_dataset


def row(text: str, label: int, group: str = "expense") -> LabeledRow:
    return LabeledRow(text=text, label=label, group=group)


def test_builds_parallel_tuples_in_order() -> None:
    ds = build_labeled_dataset([row("Gojek ride", 1), row("Indomaret", 2, "income")])
    assert ds.texts == ("Gojek ride", "Indomaret")
    assert ds.labels == (1, 2)
    assert ds.groups == ("expense", "income")
    assert len(ds) == 2


def test_duplicate_descriptions_resolve_to_the_most_recent_label() -> None:
    rows = [row("Gojek Ride", 1), row("Alfamart", 2), row("gojek  ride!", 3)]
    ds = build_labeled_dataset(rows)
    assert len(ds) == 2  # "Gojek Ride" and "gojek  ride!" clean to the same text
    assert dict(zip(ds.texts, ds.labels, strict=True))["gojek  ride!"] == 3


def test_descriptions_without_usable_tokens_are_dropped() -> None:
    ds = build_labeled_dataset([row("12345", 1), row("   ", 1), row("Spotify", 2)])
    assert ds.texts == ("Spotify",)


def test_subset_keeps_columns_aligned() -> None:
    ds = build_labeled_dataset([row("a b", 1), row("c d", 2), row("e f", 3)])
    sub = ds.subset([2, 0])
    assert sub.texts == ("e f", "a b")
    assert sub.labels == (3, 1)
