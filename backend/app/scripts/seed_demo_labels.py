"""Add ~80 varied transactions so the classifier has something real to learn from.

Run after init_db, with the backend running on :8000:
    python -m app.scripts.seed_demo_labels
Then train:  python -m app.scripts.train_classifier
"""

import datetime as dt

from app.scripts.seed_demo import call, month_start

# (type, category) -> (base amount, descriptions)
EXAMPLES: dict[tuple[str, str], tuple[int, list[str]]] = {
    ("expense", "Groceries"): (
        180_000,
        [
            "Indomaret groceries",
            "Alfamart snacks",
            "Superindo vegetables",
            "Pasar Minggu fruit",
            "Hypermart weekly shop",
            "Farmers market eggs",
            "Indomaret mineral water",
            "Alfamidi rice",
        ],
    ),
    ("expense", "Dining/Coffee"): (
        75_000,
        [
            "Kopi Kenangan latte",
            "Starbucks coffee",
            "Warung makan lunch",
            "Bakmi GM dinner",
            "Sate Khas Senayan",
            "Janji Jiwa coffee",
            "McDonalds meal",
            "Nasi goreng delivery",
        ],
    ),
    ("expense", "Transportation"): (
        60_000,
        [
            "Gojek ride to office",
            "Grab car airport",
            "Commuter line card top up",
            "Transjakarta e-money",
            "Pertamina fuel",
            "Toll road e-toll top up",
            "Parking at mall",
            "Gojek bike home",
        ],
    ),
    ("expense", "Utilities"): (
        220_000,
        [
            "PLN electricity token",
            "PDAM water bill",
            "Indihome internet bill",
            "Telkomsel data package",
            "Gas LPG refill",
            "Trash collection fee",
            "XL data package",
            "Wifi monthly bill",
        ],
    ),
    ("expense", "Subscriptions"): (
        60_000,
        [
            "Spotify premium",
            "Netflix subscription",
            "YouTube Premium",
            "iCloud storage",
            "ChatGPT subscription",
            "Disney Hotstar plan",
            "Canva Pro subscription",
            "Google One storage",
        ],
    ),
    ("expense", "Entertainment"): (
        110_000,
        [
            "Cinema tickets XXI",
            "Steam game purchase",
            "Concert ticket",
            "Bowling with friends",
            "Karaoke night",
            "Board game cafe",
            "Museum entry",
            "Mobile game top up",
        ],
    ),
    ("expense", "Healthcare"): (
        150_000,
        [
            "Kimia Farma pharmacy",
            "Doctor consultation fee",
            "Dental checkup",
            "Blood test lab",
            "Vitamins purchase",
            "Eye glasses checkup",
            "Hospital registration fee",
            "Halodoc consultation",
        ],
    ),
    ("expense", "Shopping"): (
        260_000,
        [
            "Tokopedia order shoes",
            "Shopee phone case",
            "Uniqlo shirt",
            "Zalora jacket",
            "IKEA desk lamp",
            "Lazada headphones",
            "Erigo hoodie",
            "Bukalapak backpack",
        ],
    ),
    ("income", "Salary"): (
        8_000_000,
        [
            "Monthly salary",
            "Salary payment company",
            "Gaji bulanan",
            "Payroll deposit",
            "Year end bonus",
            "Overtime pay",
            "Thirteenth month salary",
            "Salary advance repayment",
        ],
    ),
    ("income", "Freelance"): (
        1_500_000,
        [
            "Logo design project",
            "Website freelance job",
            "Client invoice paid",
            "Translation gig payment",
            "Video editing project",
            "Tutoring fee",
            "Photography gig",
            "App development milestone",
        ],
    ),
}


def main() -> None:
    today = dt.date.today()
    ids = {(c["type"], c["name"]): c["id"] for c in call("GET", "/categories")}
    created = 0
    for (kind, category), (base, descriptions) in EXAMPLES.items():
        for i, description in enumerate(descriptions):
            day = month_start(i % 6, today).replace(day=3 + (i * 3) % 24)
            if day > today:
                day = today
            call(
                "POST",
                "/transactions",
                {
                    "amount": round(base * (1 + 0.1 * (i % 5)) / 1000) * 1000,
                    "type": kind,
                    "date": day.isoformat(),
                    "description": description,
                    "category_id": ids[kind, category],
                },
            )
            created += 1
    print(f"Created {created} labelled demo transactions.")


if __name__ == "__main__":
    main()
