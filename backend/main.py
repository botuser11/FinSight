import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base, SessionLocal
from routers import auth as auth_router
from routers import banking as banking_router
import models

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

app = FastAPI(title='FinSight API')

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        FRONTEND_URL,
    ],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

@app.on_event('startup')
def startup_event():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existing = db.query(models.Category).count()
        if existing == 0:
            defaults = [
                ('Groceries', '#1D9E75'),
                ('Transport', '#534AB7'),
                ('Dining', '#BA7517'),
                ('Subscriptions', '#D85A30'),
                ('Utilities', '#378ADD'),
                ('Income', '#1D9E75'),
                ('Other', '#888780'),
            ]
            for name, color in defaults:
                category = models.Category(name=name, color_hex=color, is_default=True)
                db.add(category)
            db.commit()
    finally:
        db.close()

from routers import transactions as transactions_router
from routers import anomalies as anomalies_router
from routers import forecast as forecast_router
from routers import insights as insights_router
app.include_router(auth_router.router)
app.include_router(banking_router.router, tags=["banking"])
app.include_router(transactions_router.router, tags=["transactions"])
app.include_router(anomalies_router.router, tags=["anomalies"])
app.include_router(forecast_router.router, tags=["forecast"])
app.include_router(insights_router.router, tags=["insights"])

@app.get('/')
def root():
    return {'status': 'FinSight API is running'}