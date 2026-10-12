from statistics import median

from models import Account, Category, Transaction

# A merchant needs this many expenses before we judge what "unusual" means for it
MIN_HISTORY = 6
# Robust z-score cut-off (median / MAD based, so past spikes don't inflate the baseline)
THRESHOLD_SPREADS = 4.0
# Ignore spikes that are small in absolute or relative terms
MIN_AMOUNT = 20.0
MIN_RATIO = 2.0


def merchant_key(tx: Transaction) -> str:
    return (tx.merchant_name or tx.description or "").strip().lower()


def is_anomalous(amount: float, history: list[float]) -> bool:
    """True if `amount` is far above what's normal for this merchant's `history` (positive amounts)."""
    med = median(history)
    if med <= 0:
        return False
    mad = median(abs(a - med) for a in history)
    # 1.4826 * MAD ~ standard deviation for normal data; floor at 10% of the median
    # so near-constant merchants (subscriptions) don't flag tiny price changes
    spread = max(1.4826 * mad, 0.1 * med)
    return amount > med + THRESHOLD_SPREADS * spread and amount >= MIN_RATIO * med and amount >= MIN_AMOUNT


def detect_anomalies(db, user_id: int) -> dict:
    """Flag expenses that are unusually large for their merchant.

    Comparing per merchant (not per category) keeps unrelated spend apart,
    e.g. £3 TfL fares and £60 fuel stops are both "Transport".
    """
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

    by_merchant: dict[str, list[Transaction]] = {}
    for tx in expenses:
        key = merchant_key(tx)
        if key:
            by_merchant.setdefault(key, []).append(tx)

    category_names: dict[int, str] = {
        c.id: c.name for c in db.query(Category).all()
    }

    # Reset all anomaly flags first (clean slate on each run)
    for tx in expenses:
        tx.is_anomaly = False
        tx.anomaly_reason = None

    flagged_total = 0
    by_category_result: dict[str, int] = {}

    for txs in by_merchant.values():
        if len(txs) < MIN_HISTORY:
            continue

        amounts = [abs(tx.amount) for tx in txs]
        usual = median(amounts)

        for tx in txs:
            abs_amount = abs(tx.amount)
            if is_anomalous(abs_amount, amounts):
                name = tx.merchant_name or tx.description
                tx.is_anomaly = True
                tx.anomaly_reason = f"{round(abs_amount / usual, 1)}x your usual {name} spend"
                cat_name = category_names.get(tx.category_id, "Other")
                by_category_result[cat_name] = by_category_result.get(cat_name, 0) + 1
                flagged_total += 1

    db.commit()

    return {"flagged": flagged_total, "by_category": by_category_result}
