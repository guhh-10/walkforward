"""Fill the running API with ~6 months of demo transactions (for trying out the UI).

Usage (backend running on :8000):  python -m app.scripts.seed_demo
"""

import datetime as dt
import json
import sys
import urllib.request
from typing import Any
from urllib.error import URLError

# 127.0.0.1, not "localhost": on Windows "localhost" resolves to ::1 first while
# uvicorn listens on IPv4 only, so every request stalls ~2s before falling back.
BASE = "http://127.0.0.1:8000/api"

# (type, category, description, base amount, day of month)
TEMPLATE: list[tuple[str, str, str, float, int]] = [
    ("income", "Salary", "Monthly salary", 8_500_000, 25),
    ("income", "Freelance", "Logo design project", 1_200_000, 12),
    ("expense", "Housing", "Kost rent", 1_800_000, 1),
    ("expense", "Utilities", "Electricity token", 250_000, 5),
    ("expense", "Groceries", "Indomaret groceries", 420_000, 8),
    ("expense", "Groceries", "Alfamart snacks", 150_000, 20),
    ("expense", "Dining/Coffee", "Kopi Kenangan", 85_000, 10),
    ("expense", "Dining/Coffee", "Warung makan lunch", 160_000, 17),
    ("expense", "Transportation", "Gojek ride", 120_000, 14),
    ("expense", "Subscriptions", "Spotify", 55_000, 3),
    ("expense", "Entertainment", "Cinema tickets", 100_000, 22),
]


def call(method: str, path: str, body: Any = None) -> Any:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        BASE + path,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except URLError:
        sys.exit("Cannot reach the API. Start it first: uvicorn app.main:app --reload")


def month_start(offset: int, today: dt.date) -> dt.date:
    index = today.year * 12 + (today.month - 1) - offset
    return dt.date(index // 12, index % 12 + 1, 1)


def main() -> None:
    today = dt.date.today()
    ids = {(c["type"], c["name"]): c["id"] for c in call("GET", "/categories")}
    created = 0
    for offset in range(5, -1, -1):
        start = month_start(offset, today)
        # Vary amounts a little so the charts are not flat lines.
        factor = 0.85 + 0.06 * ((start.month * 7) % 5)
        for kind, category, description, amount, day in TEMPLATE:
            date = start.replace(day=min(day, 28))
            if date > today:  # keep the current month realistic
                continue
            scale = 1 if category in ("Salary", "Housing") else factor
            call(
                "POST",
                "/transactions",
                {
                    "amount": round(amount * scale / 1000) * 1000,
                    "type": kind,
                    "date": date.isoformat(),
                    "description": description,
                    "category_id": ids[kind, category],
                },
            )
            created += 1
    print(f"Created {created} demo transactions.")


if __name__ == "__main__":
    main()
