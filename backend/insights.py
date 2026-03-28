from collections import defaultdict
from datetime import datetime, timedelta

from models import Account, Category, Transaction


def _account_ids(db, user_id: int) -> list[int]:
    return [a.id for a in db.query(Account).filter(Account.user_id == user_id).all()]


def _category_name(db, category_id) -> str:
    if not category_id:
        return "Other"
    cat = db.query(Category).filter(Category.id == category_id).first()
    return cat.name if cat else "Other"


def detect_subscriptions(db, user_id: int) -> list:
    account_ids = _account_ids(db, user_id)
    if not account_ids:
        return []

    expenses = (
        db.query(Transaction)
        .filter(
            Transaction.account_id.in_(account_ids),
            Transaction.amount < 0,
            Transaction.merchant_name.isnot(None),
        )
        .order_by(Transaction.merchant_name, Transaction.timestamp.asc())
        .all()
    )

    # Group by merchant
    by_merchant: dict[str, list[Transaction]] = defaultdict(list)
    for tx in expenses:
        name = (tx.merchant_name or "").strip()
        if name:
            by_merchant[name].append(tx)

    results = []
    for merchant, txs in by_merchant.items():
        if len(txs) < 2:
            continue

        amounts = [abs(tx.amount) for tx in txs]
        mean_amount = sum(amounts) / len(amounts)

        # Check amounts are within 30% of each other
        if not all(abs(a - mean_amount) / mean_amount <= 0.30 for a in amounts):
            continue

        # Calculate average gap to determine frequency label
        gaps = []
        for i in range(1, len(txs)):
            delta = (txs[i].timestamp - txs[i - 1].timestamp).days
            gaps.append(abs(delta))

        if not gaps:
            continue

        avg_gap = sum(gaps) / len(gaps)

        if 20 <= avg_gap <= 40:
            frequency = "monthly"
        elif 5 <= avg_gap <= 10:
            frequency = "weekly"
        else:
            frequency = "irregular"

        most_recent = txs[-1]
        results.append({
            "merchant": merchant,
            "amount": round(abs(most_recent.amount), 2),
            "frequency": frequency,
            "total_paid": round(sum(amounts), 2),
            "occurrences": len(txs),
            "last_charged": most_recent.timestamp.isoformat(),
            "category": _category_name(db, most_recent.category_id),
        })

    results.sort(key=lambda x: x["total_paid"], reverse=True)
    return results


def detect_trends(db, user_id: int) -> list:
    account_ids = _account_ids(db, user_id)
    if not account_ids:
        return []

    now = datetime.utcnow()
    current_start = now - timedelta(days=30)
    previous_start = now - timedelta(days=60)

    expenses = (
        db.query(Transaction)
        .filter(
            Transaction.account_id.in_(account_ids),
            Transaction.amount < 0,
            Transaction.timestamp >= previous_start,
        )
        .all()
    )

    current: dict[int, float] = defaultdict(float)
    previous: dict[int, float] = defaultdict(float)

    for tx in expenses:
        if tx.timestamp >= current_start:
            current[tx.category_id] += abs(tx.amount)
        else:
            previous[tx.category_id] += abs(tx.amount)

    all_cat_ids = set(current.keys()) | set(previous.keys())
    results = []

    for cat_id in all_cat_ids:
        cur = current.get(cat_id, 0.0)
        prev = previous.get(cat_id, 0.0)

        if cur < 10 or prev < 10:
            continue
        if prev == 0:
            continue

        change_pct = ((cur - prev) / prev) * 100

        if abs(change_pct) <= 20:
            continue

        results.append({
            "category": _category_name(db, cat_id),
            "current": round(cur, 2),
            "previous": round(prev, 2),
            "change_pct": round(change_pct, 1),
            "direction": "up" if change_pct > 0 else "down",
        })

    results.sort(key=lambda x: abs(x["change_pct"]), reverse=True)
    return results


def detect_price_increases(db, user_id: int) -> list:
    subscriptions = detect_subscriptions(db, user_id)
    account_ids = _account_ids(db, user_id)
    if not account_ids:
        return []

    results = []
    for sub in subscriptions:
        merchant = sub["merchant"]

        txs = (
            db.query(Transaction)
            .filter(
                Transaction.account_id.in_(account_ids),
                Transaction.amount < 0,
                Transaction.merchant_name == merchant,
            )
            .order_by(Transaction.timestamp.asc())
            .all()
        )

        if len(txs) < 2:
            continue

        old_amount = abs(txs[0].amount)
        new_amount = abs(txs[-1].amount)

        if old_amount == 0:
            continue

        increase_pct = ((new_amount - old_amount) / old_amount) * 100

        if increase_pct > 5:
            results.append({
                "merchant": merchant,
                "old_amount": round(old_amount, 2),
                "new_amount": round(new_amount, 2),
                "increase_pct": round(increase_pct, 1),
                "since": txs[0].timestamp.isoformat(),
            })

    return results
