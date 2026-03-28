from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from insights import detect_price_increases, detect_subscriptions, detect_trends

router = APIRouter(prefix="/insights")


@router.get("/subscriptions")
def get_subscriptions(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return detect_subscriptions(db, current_user.id)


@router.get("/trends")
def get_trends(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return detect_trends(db, current_user.id)


@router.get("/price-alerts")
def get_price_alerts(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return detect_price_increases(db, current_user.id)
