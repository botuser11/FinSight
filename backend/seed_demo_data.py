"""
Seed script — creates a demo user and 12 months of realistic transactions
ending today. Runs on every backend startup and is idempotent; the demo
user's data is wiped and regenerated when it goes stale.

Usage:
    python seed_demo_data.py

Demo credentials:
    Email:    demo@finsight.app
    Password: demo1234
"""

import calendar
import logging
import random
import uuid
from datetime import datetime, timedelta

from sqlalchemy import func, insert

from anomaly_detector import detect_anomalies
from config import DEMO_EMAIL, DEMO_PASSWORD
from database import SessionLocal, ensure_schema
from models import Account, AppMeta, Category, Transaction, User
from auth import hash_password

logger = logging.getLogger("finsight.seed")

# ── configuration ────────────────────────────────────────────────────────────

MONTHS_OF_HISTORY = 12
# Bump whenever generate_transactions() changes what the demo shows;
# the demo user is re-seeded when the stored version differs.
SEED_VERSION = 2
SEED_VERSION_KEY = "demo_seed_version"
# Regenerate demo data once its latest transaction is older than this
STALE_AFTER = timedelta(days=3)

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

# Subscriptions: fixed monthly price, charged on the same day each month.
# (merchant, price, new_price, months_ago_price_changed)
SUBSCRIPTIONS = [
    ("Netflix",        15.99, 17.99, 4),   # one real price rise -> price alert
    ("Spotify",        11.99, None,  None),
    ("Amazon Prime",    8.99, None,  None),
    ("Disney+",         4.99, None,  None),
    ("Apple iCloud",    0.99, None,  None),
    ("GitHub",          3.80, None,  None),
    ("Gym Membership", 32.00, None,  None),
]

# A handful of believable one-off spikes: (months_ago, merchant, amount, description)
ANOMALIES = [
    (9, "Ocado",     264.30, "OCADO CHRISTMAS ORDER"),
    (6, "Uber",       68.40, "UBER AIRPORT TRIP"),
    (4, "Amazon",    489.99, "AMAZON MARKETPLACE"),
    (2, "Trainline", 246.50, "TRAINLINE OPEN RETURN"),
    (1, "Deliveroo", 118.75, "DELIVEROO GROUP ORDER"),
]

# Recent purchases the rules can't classify, left "pending" for "Categorise with AI"
UNCATEGORISED = [
    (2,  "Waterstones",   18.99),
    (4,  "Pret A Manger",  7.45),
    (6,  "IKEA",          86.00),
    (8,  "Odeon Cinema",  24.50),
    (10, "Ryanair",       59.99),
    (12, "Wagamama",      31.20),
]

# Monthly salary credit
INCOME_AMOUNT = (2400, 2800)


# ── helpers ───────────────────────────────────────────────────────────────────

def random_day_in_month(rng: random.Random, year: int, month: int) -> datetime:
    last_day = calendar.monthrange(year, month)[1]
    day = rng.randint(1, last_day)
    hour = rng.randint(7, 22)
    minute = rng.randint(0, 59)
    return datetime(year, month, day, hour, minute)


def months_ago(now: datetime, n: int) -> tuple[int, int]:
    month = now.month - n
    year = now.year
    while month <= 0:
        month += 12
        year -= 1
    return year, month


def generate_transactions(account_id: int, cat_map: dict[str, int], now: datetime) -> list[dict]:
    """12 months of rows ending at `now`. Nothing is dated after `now`."""
    rng = random.Random(42)  # reproducible
    rows: list[dict] = []
    sub_days = {name: rng.randint(1, 5) for name, *_ in SUBSCRIPTIONS}

    def add(merchant: str, description: str, category: str | None, amount: float, ts: datetime):
        if ts > now:
            return
        rows.append({
            "account_id": account_id,
            "truelayer_tx_id": str(uuid.uuid4()),
            "amount": amount,
            "currency": "GBP",
            "merchant_name": merchant,
            "description": description,
            "timestamp": ts,
            "category_id": cat_map[category] if category else None,
            "categorisation_source": "rule" if category else "pending",
            "is_anomaly": False,
        })

    for month_offset in range(MONTHS_OF_HISTORY - 1, -1, -1):
        year, month = months_ago(now, month_offset)

        # ── salary credit: the 1st, so the current month always has income ──
        salary_day = min(datetime(year, month, 1, 9, 0), now)
        add("Employer Payroll", "BACS SALARY", "Income", round(rng.uniform(*INCOME_AMOUNT), 2), salary_day)

        # ── expenses ─────────────────────────────────────────────────────
        for merchant, category, amt_range, freq in EXPENSE_TEMPLATES:
            # Jitter frequency slightly
            for _ in range(max(1, freq + rng.randint(-1, 1))):
                amount = -round(rng.uniform(*amt_range), 2)
                add(merchant, merchant.upper(), category, amount, random_day_in_month(rng, year, month))

        for merchant, price, new_price, changed_months_ago in SUBSCRIPTIONS:
            if new_price is not None and month_offset < changed_months_ago:
                price = new_price
            charge_day = datetime(year, month, sub_days[merchant], 10, 0)
            add(merchant, merchant.upper(), "Subscriptions", -price, charge_day)

        for anomaly_months_ago, merchant, amount, description in ANOMALIES:
            if anomaly_months_ago == month_offset:
                category = next(c for m, c, *_ in EXPENSE_TEMPLATES if m == merchant)
                add(merchant, description, category, -amount, random_day_in_month(rng, year, month))

    for days_ago, merchant, amount in UNCATEGORISED:
        ts = (now - timedelta(days=days_ago)).replace(hour=13, minute=0, second=0, microsecond=0)
        add(merchant, merchant.upper(), None, -amount, ts)

    return rows


def _demo_account(db) -> Account | None:
    user = db.query(User).filter(User.email == DEMO_EMAIL).first()
    if not user:
        return None
    return db.query(Account).filter(Account.truelayer_account_id == f"demo-account-{user.id}").first()


def _stored_seed_version(db) -> str | None:
    meta = db.get(AppMeta, SEED_VERSION_KEY)
    return meta.value if meta else None


def _regenerate(db, account: Account) -> int:
    """Replace the demo account's transactions with a fresh 12 months ending now."""
    cat_map = {c.name: c.id for c in db.query(Category).all()}
    now = datetime.utcnow()
    db.query(Transaction).filter(Transaction.account_id == account.id).delete(synchronize_session=False)
    rows = generate_transactions(account.id, cat_map, now)
    db.execute(insert(Transaction), rows)
    account.last_synced_at = now
    db.merge(AppMeta(key=SEED_VERSION_KEY, value=str(SEED_VERSION)))
    db.commit()
    # Flag anomalies up front so the demo's Anomalies page isn't empty
    detect_anomalies(db, account.user_id)
    return len(rows)


def demo_needs_reseed(db, account: Account) -> bool:
    if _stored_seed_version(db) != str(SEED_VERSION):
        return True
    latest = (
        db.query(func.max(Transaction.timestamp))
        .filter(Transaction.account_id == account.id)
        .scalar()
    )
    now = datetime.utcnow()
    # Missing, stale, or future-dated (older seeds) data all trigger a re-seed
    return latest is None or not (now - STALE_AFTER <= latest <= now)


def _reset_demo_uncategorised(db, account: Account):
    """Put the demo's unknown merchants back to "pending" so every visitor can try
    "Categorise with AI" (repeat runs are served from the merchant cache)."""
    db.query(Transaction).filter(
        Transaction.account_id == account.id,
        Transaction.merchant_name.in_([m for _, m, _ in UNCATEGORISED]),
    ).update({"category_id": None, "categorisation_source": "pending"}, synchronize_session=False)
    db.commit()


def refresh_demo_if_stale(db) -> bool:
    """Cheap checks (one key lookup + one MAX query + one UPDATE) run on startup and on demo login."""
    account = _demo_account(db)
    if not account:
        return False
    if not demo_needs_reseed(db, account):
        _reset_demo_uncategorised(db, account)
        return False
    previous_version = _stored_seed_version(db)
    count = _regenerate(db, account)
    logger.info(
        "Regenerated %s demo transactions (seed version %s -> %s)", count, previous_version, SEED_VERSION
    )
    return True


# ── main ──────────────────────────────────────────────────────────────────────

def seed():
    ensure_schema()
    db = SessionLocal()

    try:
        # ── categories ──────────────────────────────────────────────────────
        for name, color in CATEGORIES:
            if not db.query(Category).filter(Category.name == name).first():
                db.add(Category(name=name, color_hex=color, is_default=True))
        db.commit()

        # ── user ────────────────────────────────────────────────────────────
        user = db.query(User).filter(User.email == DEMO_EMAIL).first()
        if not user:
            user = User(email=DEMO_EMAIL, password_hash=hash_password(DEMO_PASSWORD))
            db.add(user)
            db.commit()
            logger.info("Created demo user %s", DEMO_EMAIL)

        # ── account ─────────────────────────────────────────────────────────
        acct_tl_id = f"demo-account-{user.id}"
        if not db.query(Account).filter(Account.truelayer_account_id == acct_tl_id).first():
            db.add(Account(
                user_id=user.id,
                truelayer_account_id=acct_tl_id,
                display_name="Demo Current Account",
                currency="GBP",
                account_type="TRANSACTION",
                last_synced_at=datetime.utcnow(),
            ))
            db.commit()
            logger.info("Created demo account")

        # ── transactions ────────────────────────────────────────────────────
        if not refresh_demo_if_stale(db):
            logger.info("Demo data is fresh; nothing to seed")

    finally:
        db.close()


if __name__ == "__main__":
    seed()
    print(f"Done. Demo credentials: {DEMO_EMAIL} / {DEMO_PASSWORD}")
