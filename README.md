# FinSight — Personal Finance Dashboard

An AI-powered personal finance dashboard with Open Banking integration, automatic transaction categorisation, anomaly detection, spending forecasts, and savings insights.

## Features

- **Open Banking** via TrueLayer OAuth2 — connect real UK bank accounts
- **Transaction categorisation** — rule-based matching + LLM fallback via OpenRouter
- **Anomaly detection** — statistical flagging using the 2σ (two standard deviations) method per category
- **Spending forecast** — exponential smoothing with trend adjustment over historical months
- **Subscription detection** — identifies recurring payments by merchant and charge pattern
- **Price increase alerts** — flags merchants whose recurring charge has risen >5%
- **Spending trends** — compares last 30 days vs prior 30 days per category
- **Dark / light mode** — persisted to localStorage, respects system preference
- **JWT authentication** — secure login and registration

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI, SQLAlchemy, SQLite (dev) / PostgreSQL (prod) |
| Frontend | React 18, Vite, Tailwind CSS, Recharts |
| Auth | JWT via python-jose |
| Open Banking | TrueLayer API |
| LLM categorisation | OpenRouter (Mistral 7B) |
| Deployment | Railway (backend), Vercel (frontend) |

## Local Development

### Prerequisites

- Python 3.11+
- Node.js 18+
- TrueLayer sandbox account — [console.truelayer.com](https://console.truelayer.com)
- OpenRouter account — [openrouter.ai](https://openrouter.ai)

### Backend setup

```bash
cd backend
cp .env.example .env
# Fill in your credentials in .env
pip install -r requirements.txt
uvicorn main:app --reload
```

API will be available at `http://localhost:8000`.
Interactive docs at `http://localhost:8000/docs`.

### Frontend setup

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

App will be available at `http://localhost:5173`.

### Environment variables

**Backend (`backend/.env`):**

```
DATABASE_URL=sqlite:///./finsight.db
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
TRUELAYER_CLIENT_ID=your-truelayer-client-id
TRUELAYER_CLIENT_SECRET=your-truelayer-client-secret
TRUELAYER_REDIRECT_URI=http://localhost:8000/banking/callback
TRUELAYER_AUTH_URL=https://auth.truelayer-sandbox.com
TRUELAYER_API_URL=https://api.truelayer-sandbox.com
OPENROUTER_API_KEY=your-openrouter-key
FRONTEND_URL=http://localhost:5173
```

**Frontend (`frontend/.env`):**

```
VITE_API_URL=http://localhost:8000
```

## Deployment

### Backend — Railway

1. Connect your GitHub repo to [Railway](https://railway.app)
2. Set the root directory to `/backend`
3. Add all environment variables from `backend/.env`
4. Update TrueLayer URLs to production endpoints:
   - `TRUELAYER_AUTH_URL=https://auth.truelayer.com`
   - `TRUELAYER_API_URL=https://api.truelayer.com`
5. Set `FRONTEND_URL` to your Vercel deployment URL
6. Set `TRUELAYER_REDIRECT_URI` to `https://your-railway-app.railway.app/banking/callback`
7. Railway detects the `Procfile` and deploys automatically

### Frontend — Vercel

1. Connect your GitHub repo to [Vercel](https://vercel.com)
2. Set the root directory to `/frontend`
3. Add environment variable: `VITE_API_URL=https://your-railway-app.railway.app`
4. Vercel detects Vite and deploys automatically
5. `vercel.json` handles SPA routing rewrites

## Architecture

The app is built across 7 modules:

| Module | Description |
|--------|-------------|
| 1 — Auth | User registration and login with JWT |
| 2 — Banking | TrueLayer OAuth2 flow, account sync, transaction import |
| 3 — Categorisation | Rule-based + LLM categorisation of transactions |
| 4 — Dashboard | Monthly overview with metric cards, spending chart, category donut |
| 5 — Anomaly Detection | Flags transactions >2σ above category mean |
| 6 — Forecast | Exponential smoothing forecast with trend detection |
| 7 — Savings Insights | Subscription detection, spending trends, price increase alerts |

```
FinSight/
├── backend/
│   ├── main.py              # FastAPI app, middleware, router registration
│   ├── models.py            # SQLAlchemy models
│   ├── database.py          # DB connection and session
│   ├── auth.py              # JWT auth helpers
│   ├── categoriser.py       # Rule-based + LLM categorisation
│   ├── anomaly_detector.py  # Statistical anomaly detection
│   ├── forecaster.py        # Exponential smoothing forecast
│   ├── insights.py          # Subscription / trend / price-increase detection
│   └── routers/
│       ├── auth.py
│       ├── banking.py
│       ├── transactions.py
│       ├── anomalies.py
│       ├── forecast.py
│       └── insights.py
└── frontend/
    └── src/
        ├── api/             # Axios API modules per domain
        ├── components/      # Layout + reusable UI components
        ├── context/         # Auth and theme context
        ├── hooks/           # Data-fetching hooks
        └── pages/           # One file per route
```
