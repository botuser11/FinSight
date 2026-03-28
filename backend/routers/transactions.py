import os
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth import get_current_user
from categoriser import OPENROUTER_API_KEY, llm_category, rule_based_category
from database import get_db
from models import Account, Category, Transaction

router = APIRouter(prefix="/transactions")


@router.get("/categories")
def get_categories(db: Session = Depends(get_db)):
    cats = db.query(Category).all()
    return [{"id": c.id, "name": c.name, "color_hex": c.color_hex} for c in cats]


class CategoryUpdate(BaseModel):
    category_id: int


def _tx_dict(tx: Transaction) -> dict:
    return {
        "id": tx.id,
        "amount": tx.amount,
        "currency": tx.currency,
        "description": tx.description,
        "merchant_name": tx.merchant_name,
        "timestamp": tx.timestamp,
        "categorisation_source": tx.categorisation_source,
        "is_anomaly": tx.is_anomaly,
        "anomaly_reason": tx.anomaly_reason,
        "category": {"id": tx.category.id, "name": tx.category.name} if tx.category else None,
    }


def _user_account_ids(current_user, db: Session) -> list[int]:
    accounts = db.query(Account.id).filter(Account.user_id == current_user.id).all()
    return [a.id for a in accounts]


@router.get("")
def get_transactions(
    month: int | None = Query(None, ge=1, le=12),
    year: int | None = Query(None),
    category_id: int | None = Query(None),
    is_anomaly: bool | None = Query(None),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(default=20, ge=1, le=500),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    account_ids = _user_account_ids(current_user, db)
    q = db.query(Transaction).filter(Transaction.account_id.in_(account_ids))

    if month is not None:
        effective_year = year or datetime.utcnow().year
        q = q.filter(Transaction.timestamp >= datetime(effective_year, month, 1))
        if month == 12:
            q = q.filter(Transaction.timestamp < datetime(effective_year + 1, 1, 1))
        else:
            q = q.filter(Transaction.timestamp < datetime(effective_year, month + 1, 1))
    elif year is not None:
        q = q.filter(
            Transaction.timestamp >= datetime(year, 1, 1),
            Transaction.timestamp < datetime(year + 1, 1, 1),
        )

    if category_id is not None:
        q = q.filter(Transaction.category_id == category_id)
    if is_anomaly is not None:
        q = q.filter(Transaction.is_anomaly == is_anomaly)
    if search:
        term = f"%{search}%"
        q = q.filter(
            Transaction.merchant_name.ilike(term) | Transaction.description.ilike(term)
        )

    total = q.count()
    txs = q.order_by(Transaction.timestamp.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return {"total": total, "page": page, "page_size": page_size, "transactions": [_tx_dict(t) for t in txs]}


@router.get("/summary")
def get_summary(
    month: int = Query(..., ge=1, le=12),
    year: int = Query(...),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    account_ids = _user_account_ids(current_user, db)

    if month == 12:
        end = datetime(year + 1, 1, 1)
    else:
        end = datetime(year, month + 1, 1)

    txs = (
        db.query(Transaction)
        .filter(
            Transaction.account_id.in_(account_ids),
            Transaction.amount < 0,
            Transaction.timestamp >= datetime(year, month, 1),
            Transaction.timestamp < end,
        )
        .all()
    )

    totals: dict[str, dict] = {}
    for tx in txs:
        name = tx.category.name if tx.category else "Other"
        if name not in totals:
            totals[name] = {"category": name, "total": 0.0, "count": 0}
        totals[name]["total"] = round(totals[name]["total"] + tx.amount, 2)
        totals[name]["count"] += 1

    return list(totals.values())


@router.post("/categorise")
def categorise_transactions(
    use_llm: bool = Query(False),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    account_ids = _user_account_ids(current_user, db)

    pending = (
        db.query(Transaction)
        .filter(
            Transaction.account_id.in_(account_ids),
            Transaction.categorisation_source == "pending",
        )
        .all()
    )

    category_map: dict[str, int] = {
        c.name: c.id for c in db.query(Category).all()
    }

    counts = {"rule": 0, "llm": 0, "other": 0}
    batch_size = 50

    for i in range(0, len(pending), batch_size):
        batch = pending[i: i + batch_size]
        for tx in batch:
            merchant = tx.merchant_name or ""
            desc = tx.description or ""

            category_name = rule_based_category(merchant, desc)
            source = "rule"

            if category_name is None:
                if use_llm and OPENROUTER_API_KEY:
                    category_name = llm_category(merchant, desc)
                    source = "llm"
                else:
                    category_name = "Other"
                    source = "other"

            if category_name not in category_map:
                category_name = "Other"
                source = "other"

            tx.category_id = category_map[category_name]
            tx.categorisation_source = source
            counts[source] += 1

        db.commit()

    return {"categorised": len(pending), "by_source": counts}


@router.get("/{tx_id}")
def get_transaction(
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
    return _tx_dict(tx)


@router.patch("/{tx_id}")
def update_transaction(
    tx_id: int,
    body: CategoryUpdate,
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

    category = db.query(Category).filter(Category.id == body.category_id).first()
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    tx.category_id = body.category_id
    tx.categorisation_source = "manual"
    db.commit()
    db.refresh(tx)
    return _tx_dict(tx)
