from statistics import mean, stdev

from models import Account, Category, Transaction


def detect_anomalies(db, user_id: int) -> dict:
    account_ids = [
        a.id for a in db.query(Account).filter(Account.user_id == user_id).all()
    ]
    if not account_ids:
        return {"flagged": 0, "by_category": {}}

    expenses = (
        db.query(Transaction)
        .filter(
            Transaction.account_id.in_(account_ids),
            Transaction.amount < 0,
        )
        .all()
    )

    # Group by category_id
    by_category: dict[int, list[Transaction]] = {}
    for tx in expenses:
        by_category.setdefault(tx.category_id, []).append(tx)

    # Build category name lookup
    category_names: dict[int, str] = {
        c.id: c.name for c in db.query(Category).all()
    }

    # Reset all anomaly flags first (clean slate on each run)
    for tx in expenses:
        tx.is_anomaly = False
        tx.anomaly_reason = None

    flagged_total = 0
    by_category_result: dict[str, int] = {}

    for cat_id, txs in by_category.items():
        if len(txs) < 5:
            continue

        amounts = [abs(tx.amount) for tx in txs]
        cat_mean = mean(amounts)

        # Skip if all amounts are identical (stdev would be 0)
        if len(set(amounts)) < 2:
            continue

        cat_std = stdev(amounts)
        if cat_std == 0:
            continue

        threshold = cat_mean + (2 * cat_std)
        cat_name = category_names.get(cat_id, "Unknown")
        flagged_in_cat = 0

        for tx in txs:
            abs_amount = abs(tx.amount)
            if abs_amount > threshold and abs_amount > 10:
                tx.is_anomaly = True
                tx.anomaly_reason = (
                    f"{round(abs_amount / cat_mean, 1)}x your {cat_name} average"
                )
                flagged_in_cat += 1

        if flagged_in_cat > 0:
            by_category_result[cat_name] = flagged_in_cat
            flagged_total += flagged_in_cat

    db.commit()

    return {"flagged": flagged_total, "by_category": by_category_result}
