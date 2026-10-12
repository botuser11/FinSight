from limiter import limiter
from tests.conftest import login


def test_register_requires_8_char_password(client):
    resp = client.post("/auth/register", json={"email": "short@example.com", "password": "1234567"})
    assert resp.status_code == 422


def test_register_login_and_me(client):
    resp = client.post("/auth/register", json={"email": "new@example.com", "password": "longenough"})
    assert resp.status_code == 200
    headers = login(client, "new@example.com", "longenough")
    me = client.get("/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email"] == "new@example.com"


def test_duplicate_registration_rejected(client):
    client.post("/auth/register", json={"email": "dupe@example.com", "password": "longenough"})
    resp = client.post("/auth/register", json={"email": "dupe@example.com", "password": "longenough"})
    assert resp.status_code == 400


def test_wrong_password_is_401(client):
    resp = client.post("/auth/login", json={"email": "demo@finsight.app", "password": "wrong-password"})
    assert resp.status_code == 401


def test_demo_login_works(client):
    login(client, "demo@finsight.app", "demo1234")


def test_categories_require_auth(client):
    assert client.get("/transactions/categories").status_code == 401


def test_login_is_rate_limited(client):
    limiter.enabled = True
    limiter.reset()
    try:
        codes = [
            client.post("/auth/login", json={"email": "nobody@example.com", "password": "whatever1"}).status_code
            for _ in range(11)
        ]
    finally:
        limiter.enabled = False
    assert codes[:10] == [401] * 10
    assert codes[10] == 429
