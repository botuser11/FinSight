from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from forecaster import forecast_spending
from models import Account, Transaction
from collections import defaultdict

router = APIRouter(prefix="/forecast")


@router.get("")
def get_forecast(
    months_ahead: int = Query(default=3, ge=1, le=12),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return forecast_spending(db, current_user.id, months_ahead)


@router.get("/history")
def get_history(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    account_ids = [
        a.id for a in db.query(Account).filter(Account.user_id == current_user.id).all()
    ]

    expenses = (
        db.query(Transaction)
        .filter(
            Transaction.account_id.in_(account_ids),
            Transaction.amount < 0,
        )
        .order_by(Transaction.timestamp.asc())
        .all()
    )

    monthly: dict[str, float] = defaultdict(float)
    for tx in expenses:
        key = tx.timestamp.strftime("%Y-%m")
        monthly[key] += abs(tx.amount)

    return [
        {"month": m, "actual": round(monthly[m], 2)}
        for m in sorted(monthly.keys())
    ]
