from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from anomaly_detector import detect_anomalies
from auth import get_current_user
from database import get_db
from models import Account, Transaction

router = APIRouter(prefix="/anomalies")


def _user_account_ids(current_user, db: Session) -> list[int]:
    return [
        a.id for a in db.query(Account).filter(Account.user_id == current_user.id).all()
    ]


@router.post("/run")
def run_detection(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return detect_anomalies(db, current_user.id)


@router.get("")
def get_anomalies(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    account_ids = _user_account_ids(current_user, db)

    txs = (
        db.query(Transaction)
        .filter(
            Transaction.account_id.in_(account_ids),
            Transaction.is_anomaly == True,
        )
        .order_by(Transaction.amount.asc())
        .all()
    )

    return [
        {
            "id": tx.id,
            "merchant_name": tx.merchant_name,
            "amount": tx.amount,
            "currency": tx.currency,
            "timestamp": tx.timestamp,
            "anomaly_reason": tx.anomaly_reason,
            "category": {"id": tx.category.id, "name": tx.category.name} if tx.category else None,
            "account_display_name": tx.account.display_name if tx.account else None,
        }
        for tx in txs
    ]


@router.patch("/{tx_id}/dismiss")
def dismiss_anomaly(
    tx_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    account_ids = _user_account_ids(current_user, db)
    tx = db.query(Transaction).filter(
        Transaction.id == tx_id,
        Transaction.account_id.in_(account_ids),
    ).first()

    if not tx:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")

    tx.is_anomaly = False
    tx.anomaly_reason = None
    db.commit()

    return {"dismissed": True}
