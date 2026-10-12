import os
import sys
import tempfile
import uuid
from datetime import datetime
from pathlib import Path

import pytest

# Configure env before any app module is imported (config/database read it at import).
_tmpdir = tempfile.mkdtemp(prefix="finsight-tests-")
os.environ["DATABASE_URL"] = f"sqlite:///{Path(_tmpdir) / 'test.db'}"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["FRONTEND_URL"] = "http://localhost:5173"
os.environ["OPENROUTER_API_KEY"] = ""
os.environ.pop("RENDER", None)
os.environ.pop("ENVIRONMENT", None)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402

from database import SessionLocal  # noqa: E402
from limiter import limiter  # noqa: E402
from main import app  # noqa: E402
from models import Account, Category, Transaction, User  # noqa: E402
from auth import hash_password  # noqa: E402

limiter.enabled = False  # individual tests switch it on when they need it


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:  # runs the lifespan: schema + demo seed
        yield c


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def login(client, email, password):
    resp = client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture
def make_user(client, db):
    """Create a user with one bank account; returns (user, account, auth headers)."""
    def _make(password="password123"):
        user = User(email=f"user-{uuid.uuid4().hex[:8]}@example.com", password_hash=hash_password(password))
        db.add(user)
        db.commit()
        account = Account(user_id=user.id, truelayer_account_id=f"acc-{uuid.uuid4().hex}", display_name="Test")
        db.add(account)
        db.commit()
        return user, account, login(client, user.email, password)
    return _make


@pytest.fixture
def add_tx(db):
    """Insert a transaction: add_tx(account, amount, when, merchant=..., category=..., source=...)."""
    categories = {c.name: c.id for c in db.query(Category).all()}

    def _add(account, amount, when: datetime, merchant="Shop", category="Other", source="rule"):
        tx = Transaction(
            account_id=account.id,
            truelayer_tx_id=uuid.uuid4().hex,
            amount=amount,
            currency="GBP",
            merchant_name=merchant,
            description=merchant.upper(),
            timestamp=when,
            category_id=categories.get(category) if category else None,
            categorisation_source=source,
        )
        db.add(tx)
        db.commit()
        return tx
    return _add
