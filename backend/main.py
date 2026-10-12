from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from config import FRONTEND_URL, IS_PRODUCTION
from limiter import limiter
from routers import auth as auth_router
from routers import banking as banking_router
from seed_demo_data import seed

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Creates tables, default categories and the demo user + data (idempotent)
    seed()
    yield


app = FastAPI(title='FinSight API', lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

allowed_origins = [FRONTEND_URL]
if not IS_PRODUCTION:
    allowed_origins += ["http://localhost:5173", "http://localhost:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
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
