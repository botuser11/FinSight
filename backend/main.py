import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base, SessionLocal
from routers import auth as auth_router
from routers import banking as banking_router
from seed_demo_data import seed

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Creates tables, default categories and the demo user + data (idempotent)
    seed()
    yield


app = FastAPI(title='FinSight API', lifespan=lifespan)

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


@app.get('/health')
def health():
    return {'status': 'ok'}
