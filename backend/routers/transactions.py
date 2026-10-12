import os
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth import get_current_user
from categoriser import (
    LLM_BATCH_SIZE,
    LLM_DAILY_CALL_LIMIT,
    OPENROUTER_API_KEY,
    llm_categorise_batch,
    normalise_merchant,
    rule_based_category,
)
from database import get_db
from models import Account, Category, LlmUsage, MerchantCategoryCache, Transaction

router = APIRouter(prefix="/transactions")


@router.get("/categories")
def get_categories(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
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
            Transaction.timestamp >= datetime(year, month, 1),
            Transaction.timestamp < end,
        )
        .all()
    )

    # All totals are positive amounts; net is signed (negative = overspent).
    income = 0.0
    spend = 0.0
    by_category: dict[str, dict] = {}
    for tx in txs:
        if tx.amount > 0:
            income += tx.amount
            continue
        spend += -tx.amount
        name = tx.category.name if tx.category else "Other"
        if name not in by_category:
            by_category[name] = {"category": name, "total": 0.0, "count": 0}
        by_category[name]["total"] += -tx.amount
        by_category[name]["count"] += 1

    for entry in by_category.values():
        entry["total"] = round(entry["total"], 2)

    return {
        "month": month,
        "year": year,
        "income": round(income, 2),
        "spend": round(spend, 2),
        "net": round(income - spend, 2),
        "by_category": sorted(by_category.values(), key=lambda e: e["total"], reverse=True),
    }


@router.post("/categorise")
def categorise_transactions(
    use_llm: bool = Query(False),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Categorise pending transactions.

    Rules first. With use_llm, merchants the rules can't place are looked up in
    the merchant cache, then sent to the LLM in batches (capped per user per day).
    Without use_llm, unmatched transactions become "Other". If the LLM is
    unavailable, fails or hits the cap, unmatched transactions stay pending so
    they can be retried.
    """
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
    counts = {"rule": 0, "llm": 0, "cache": 0, "other": 0}

    def assign(tx: Transaction, category_name: str, source: str):
        if category_name not in category_map:
            category_name, source = "Other", "other"
        tx.category_id = category_map[category_name]
        tx.categorisation_source = "llm" if source == "cache" else source
        counts[source] += 1

    unmatched: list[Transaction] = []
    for tx in pending:
        category_name = rule_based_category(tx.merchant_name or "", tx.description or "")
        if category_name:
            assign(tx, category_name, "rule")
        else:
            unmatched.append(tx)

    usage = None
    llm_status = "not_needed"
    if unmatched and not use_llm:
        for tx in unmatched:
            assign(tx, "Other", "other")
        unmatched = []
    elif unmatched:
        by_merchant: dict[str, list[Transaction]] = {}
        for tx in unmatched:
            by_merchant.setdefault(normalise_merchant(tx.merchant_name or tx.description), []).append(tx)

        cached = {
            row.merchant: row.category
            for row in db.query(MerchantCategoryCache)
            .filter(MerchantCategoryCache.merchant.in_(list(by_merchant)))
            .all()
        }
        for merchant, category_name in cached.items():
            for tx in by_merchant.pop(merchant):
                assign(tx, category_name, "cache")

        today = datetime.utcnow().date()
        usage = db.get(LlmUsage, (current_user.id, today))
        if usage is None:
            usage = LlmUsage(user_id=current_user.id, day=today, calls=0)
            db.add(usage)

        llm_status = "ok"
        if by_merchant and not OPENROUTER_API_KEY:
            llm_status = "disabled"
        merchants = list(by_merchant)
        for i in range(0, len(merchants) if OPENROUTER_API_KEY else 0, LLM_BATCH_SIZE):
            if usage.calls >= LLM_DAILY_CALL_LIMIT:
                llm_status = "limit_reached"
                break
            batch = merchants[i: i + LLM_BATCH_SIZE]
            usage.calls += 1
            answers = llm_categorise_batch(batch)
            if answers is None:
                llm_status = "failed"
                break
            for merchant, category_name in answers.items():
                db.merge(MerchantCategoryCache(merchant=merchant, category=category_name))
                for tx in by_merchant.pop(merchant):
                    assign(tx, category_name, "llm")

        unmatched = [tx for txs in by_merchant.values() for tx in txs]

    db.commit()

    return {
        "categorised": len(pending) - len(unmatched),
        "pending": len(unmatched),
        "by_source": counts,
        "llm": {
            "status": llm_status,
            "calls_today": usage.calls if usage else None,
            "daily_limit": LLM_DAILY_CALL_LIMIT,
        },
    }


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
