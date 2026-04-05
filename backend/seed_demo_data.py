"""
Seed script — creates a demo user and 12 months of realistic transactions.

Usage:
    python seed_demo_data.py

Demo credentials:
    Email:    demo@finsight.app
    Password: demo1234
"""

import random
import uuid
from datetime import datetime, timedelta

from database import Base, SessionLocal, engine
from models import Account, Category, Transaction, User
from auth import hash_password

# ── configuration ────────────────────────────────────────────────────────────

DEMO_EMAIL = "demo@finsight.app"
DEMO_PASSWORD = "demo1234"
MONTHS_OF_HISTORY = 12

CATEGORIES = [
    ("Groceries",     "#1D9E75"),
    ("Transport",     "#534AB7"),
    ("Dining",        "#BA7517"),
    ("Subscriptions", "#D85A30"),
    ("Utilities",     "#378ADD"),
    ("Income",        "#1D9E75"),
    ("Other",         "#888780"),
]

# (merchant, category, amount_range, monthly_frequency)
EXPENSE_TEMPLATES = [
    # Groceries
    ("Tesco",               "Groceries",     (15, 90),   8),
    ("Sainsbury's",         "Groceries",     (20, 75),   6),
    ("Lidl",                "Groceries",     (10, 55),   5),
    ("Ocado",               "Groceries",     (60, 130),  2),
    # Transport
    ("TfL",                 "Transport",     (2, 6),    20),
    ("Trainline",           "Transport",     (18, 85),   3),
    ("Uber",                "Transport",     (8, 25),    6),
    ("Shell",               "Transport",     (40, 75),   2),
    # Dining
    ("Deliveroo",           "Dining",        (15, 45),   5),
    ("McDonald's",          "Dining",        (5, 14),    4),
    ("Costa Coffee",        "Dining",        (3, 7),     8),
    ("Nando's",             "Dining",        (14, 28),   2),
    ("Starbucks",           "Dining",        (4, 8),     6),
    ("Just Eat",            "Dining",        (18, 40),   3),
    # Subscriptions (fixed-ish amounts)
    ("Netflix",             "Subscriptions", (15, 18),   1),
    ("Spotify",             "Subscriptions", (10, 11),   1),
    ("Amazon Prime",        "Subscriptions", (8, 9),     1),
    ("Disney+",             "Subscriptions", (4, 5),     1),
    ("Apple",               "Subscriptions", (0, 1),     1),  # iCloud
    ("GitHub",              "Subscriptions", (3, 4),     1),
    ("Gym Membership",      "Subscriptions", (30, 35),   1),
    # Utilities
    ("British Gas",         "Utilities",     (45, 110),  1),
    ("Thames Water",        "Utilities",     (28, 42),   1),
    ("BT",                  "Utilities",     (38, 55),   1),
    ("Vodafone",            "Utilities",     (22, 32),   1),
    # Other
    ("Amazon",              "Other",         (8, 120),   4),
    ("ASOS",                "Other",         (20, 80),   2),
    ("Boots",               "Other",         (5, 35),    3),
]

# Monthly salary credit
INCOME_AMOUNT = (2400, 2800)


# ── helpers ───────────────────────────────────────────────────────────────────

def random_day_in_month(year: int, month: int) -> datetime:
    import calendar
    last_day = calendar.monthrange(year, month)[1]
    day = random.randint(1, last_day)
    hour = random.randint(7, 22)
    minute = random.randint(0, 59)
    return datetime(year, month, day, hour, minute)


def months_ago(n: int) -> tuple[int, int]:
    now = datetime.utcnow()
    month = now.month - n
    year = now.year
    while month <= 0:
        month += 12
        year -= 1
    return year, month


# ── main ──────────────────────────────────────────────────────────────────────

def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # ── categories ──────────────────────────────────────────────────────
        cat_map: dict[str, int] = {}
        for name, color in CATEGORIES:
            existing = db.query(Category).filter(Category.name == name).first()
            if existing:
                cat_map[name] = existing.id
            else:
                cat = Category(name=name, color_hex=color, is_default=True)
                db.add(cat)
                db.flush()
                cat_map[name] = cat.id
        db.commit()
        print(f"  OK{len(cat_map)} categories ready")

        # ── user ────────────────────────────────────────────────────────────
        user = db.query(User).filter(User.email == DEMO_EMAIL).first()
        if not user:
            user = User(email=DEMO_EMAIL, password_hash=hash_password(DEMO_PASSWORD))
            db.add(user)
            db.flush()
            db.commit()
            print(f"  OKCreated user {DEMO_EMAIL}")
        else:
            print(f"  OKUser {DEMO_EMAIL} already exists (id={user.id})")

        # ── account ─────────────────────────────────────────────────────────
        acct_tl_id = f"demo-account-{user.id}"
        account = db.query(Account).filter(Account.truelayer_account_id == acct_tl_id).first()
        if not account:
            account = Account(
                user_id=user.id,
                truelayer_account_id=acct_tl_id,
                display_name="Demo Current Account",
                currency="GBP",
                account_type="TRANSACTION",
                last_synced_at=datetime.utcnow(),
            )
            db.add(account)
            db.flush()
            db.commit()
            print(f"  OKCreated account (id={account.id})")
        else:
            print(f"  OKAccount already exists (id={account.id})")

        # ── transactions ────────────────────────────────────────────────────
        existing_tx_count = (
            db.query(Transaction)
            .filter(Transaction.account_id == account.id)
            .count()
        )
        if existing_tx_count > 0:
            print(f"  OK{existing_tx_count} transactions already exist — skipping generation")
            return

        tx_count = 0
        random.seed(42)  # reproducible

        for month_offset in range(MONTHS_OF_HISTORY - 1, -1, -1):
            year, month = months_ago(month_offset)

            # ── salary credit ────────────────────────────────────────────
            salary_day = datetime(year, month, random.randint(25, 28), 9, 0)
            salary_amount = round(random.uniform(*INCOME_AMOUNT), 2)
            db.add(Transaction(
                account_id=account.id,
                truelayer_tx_id=str(uuid.uuid4()),
                amount=salary_amount,
                currency="GBP",
                merchant_name="Employer Payroll",
                description="BACS SALARY",
                timestamp=salary_day,
                category_id=cat_map["Income"],
                categorisation_source="rule",
                is_anomaly=False,
            ))
            tx_count += 1

            # ── expenses ─────────────────────────────────────────────────
            for merchant, category, amt_range, freq in EXPENSE_TEMPLATES:
                # Subscriptions: one charge per month on a consistent day
                if category == "Subscriptions":
                    charge_day = datetime(year, month, random.randint(1, 5), 10, 0)
                    amount = -round(random.uniform(*amt_range) + random.uniform(0, 0.99), 2)
                    db.add(Transaction(
                        account_id=account.id,
                        truelayer_tx_id=str(uuid.uuid4()),
                        amount=amount,
                        currency="GBP",
                        merchant_name=merchant,
                        description=merchant.upper(),
                        timestamp=charge_day,
                        category_id=cat_map[category],
                        categorisation_source="rule",
                        is_anomaly=False,
                    ))
                    tx_count += 1
                else:
                    # Jitter frequency slightly
                    actual_freq = max(1, freq + random.randint(-1, 1))
                    for _ in range(actual_freq):
                        ts = random_day_in_month(year, month)
                        amount = -round(random.uniform(*amt_range), 2)
                        db.add(Transaction(
                            account_id=account.id,
                            truelayer_tx_id=str(uuid.uuid4()),
                            amount=amount,
                            currency="GBP",
                            merchant_name=merchant,
                            description=merchant.upper(),
                            timestamp=ts,
                            category_id=cat_map[category],
                            categorisation_source="rule",
                            is_anomaly=False,
                        ))
                        tx_count += 1

            # Inject 1-2 anomalous transactions per month
            for _ in range(random.randint(1, 2)):
                anomaly_merchant, anomaly_cat, anomaly_range, _ = random.choice(EXPENSE_TEMPLATES)
                ts = random_day_in_month(year, month)
                # 4-6x the normal upper bound
                amount = -round(random.uniform(anomaly_range[1] * 4, anomaly_range[1] * 6), 2)
                db.add(Transaction(
                    account_id=account.id,
                    truelayer_tx_id=str(uuid.uuid4()),
                    amount=amount,
                    currency="GBP",
                    merchant_name=anomaly_merchant,
                    description=f"{anomaly_merchant.upper()} LARGE",
                    timestamp=ts,
                    category_id=cat_map[anomaly_cat],
                    categorisation_source="rule",
                    is_anomaly=False,
                ))
                tx_count += 1

        db.commit()
        print(f"  OKCreated {tx_count} transactions across {MONTHS_OF_HISTORY} months")
        print()
        print("  Demo credentials:")
        print(f"    Email:    {DEMO_EMAIL}")
        print(f"    Password: {DEMO_PASSWORD}")

    finally:
        db.close()


if __name__ == "__main__":
    print("Seeding demo data…")
    seed()
    print("Done.")
