"""Text cleaning for transaction descriptions. Pure and picklable.

`clean_text` is used as the vectorizers' preprocessor inside the sklearn Pipeline,
so training and prediction always clean text the same way.
"""

import re

_PUNCTUATION = re.compile(r"[^\w\s]|_")


def clean_text(text: str) -> str:
    """Lowercase, strip punctuation, drop pure-numeric tokens, collapse whitespace.

    >>> clean_text("Gojek*Ride 85000, Jakarta!")
    'gojek ride jakarta'
    """
    without_punctuation = _PUNCTUATION.sub(" ", text.lower())
    tokens = [t for t in without_punctuation.split() if not t.isdigit()]
    return " ".join(tokens)
