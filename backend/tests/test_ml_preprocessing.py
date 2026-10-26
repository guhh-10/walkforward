import pytest
from app.ml.preprocessing import clean_text


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Gojek*Ride 85000, Jakarta!", "gojek ride jakarta"),
        ("  Indomaret   GROCERIES  ", "indomaret groceries"),
        ("Dining/Coffee", "dining coffee"),
        ("7-Eleven 24/7", "eleven"),  # pure-numeric tokens are dropped
        ("kopi_kenangan #12", "kopi kenangan"),
        ("Order A1 5000", "order a1"),  # alphanumeric tokens survive
        ("   ", ""),
        ("12345 67890", ""),
    ],
)
def test_clean_text(raw: str, expected: str) -> None:
    assert clean_text(raw) == expected
