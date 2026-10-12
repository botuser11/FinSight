from datetime import datetime

from models import Account, Transaction
from tests.conftest import login


def test_disconnect_removes_accounts_and_their_transactions(client, make_user, add_tx, db):
    user, account, headers = make_user()
    add_tx(account, -10.0, datetime(2026, 1, 1))
    add_tx(account, -20.0, datetime(2026, 1, 2))
    account_id = account.id

    resp = client.delete("/banking/disconnect", headers=headers)

    assert resp.status_code == 200
    assert resp.json() == {"disconnected": True, "accounts_removed": 1, "transactions_removed": 2}
    db.expire_all()
    assert db.query(Account).filter(Account.user_id == user.id).count() == 0
    assert db.query(Transaction).filter(Transaction.account_id == account_id).count() == 0


def test_demo_account_cannot_connect_sync_or_disconnect(client):
    headers = login(client, "demo@finsight.app", "demo1234")
    assert client.get("/banking/connect", headers=headers).status_code == 403
    assert client.post("/banking/sync", headers=headers).status_code == 403
    assert client.delete("/banking/disconnect", headers=headers).status_code == 403


def test_callback_rejects_missing_or_forged_state(client):
    forged_state = "eyJ1c2VyX2lkIjogMX0="  # base64 of {"user_id": 1}, the old unsigned format
    for params in ({"code": "x"}, {"code": "x", "state": forged_state}):
        resp = client.get("/banking/callback", params=params, follow_redirects=False)
        assert resp.status_code == 302
        assert resp.headers["location"].endswith("/dashboard?error=true")
