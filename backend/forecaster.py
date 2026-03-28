from collections import defaultdict
from datetime import datetime

from models import Account, Transaction


def forecast_spending(db, user_id: int, months_ahead: int = 1) -> dict:
    account_ids = [
        a.id for a in db.query(Account).filter(Account.user_id == user_id).all()
    ]
    if not account_ids:
        return {"error": "No accounts found"}

    expenses = (
        db.query(Transaction)
        .filter(
            Transaction.account_id.in_(account_ids),
            Transaction.amount < 0,
        )
        .order_by(Transaction.timestamp.asc())
        .all()
    )

    if not expenses:
        return {"error": "Not enough data"}

    # Group by year-month and sum absolute amounts
    monthly: dict[str, float] = defaultdict(float)
    for tx in expenses:
        key = tx.timestamp.strftime("%Y-%m")
        monthly[key] += abs(tx.amount)

    # Sort chronologically
    sorted_months = sorted(monthly.keys())
    monthly_totals = [monthly[m] for m in sorted_months]

    if len(monthly_totals) < 3:
        return {"error": "Not enough data"}

    # Exponential smoothing
    alpha = 0.3
    smoothed = [monthly_totals[0]]
    for v in monthly_totals[1:]:
        smoothed.append(alpha * v + (1 - alpha) * smoothed[-1])

    # Trend: average change over last 2 steps
    trend = (smoothed[-1] - smoothed[-3]) / 2

    # Build forecast months
    last_month = datetime.strptime(sorted_months[-1], "%Y-%m")
    forecast_entries = []
    for i in range(1, months_ahead + 1):
        predicted = smoothed[-1] + (trend * i)
        predicted = max(0.0, predicted)

        # Advance month
        m = last_month.month + i
        y = last_month.year + (m - 1) // 12
        m = ((m - 1) % 12) + 1
        label = f"{y}-{m:02d}"
        forecast_entries.append({"month": label, "predicted": round(predicted, 2)})

    # Trend label
    if abs(trend) < 50:
        trend_label = "stable"
    elif trend > 0:
        trend_label = "increasing"
    else:
        trend_label = "decreasing"

    historical = [
        {"month": m, "actual": round(monthly[m], 2)} for m in sorted_months
    ]

    return {
        "historical": historical,
        "forecast": forecast_entries,
        "current_month_predicted": forecast_entries[0]["predicted"] if forecast_entries else 0,
        "trend": trend_label,
    }
