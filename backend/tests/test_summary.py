from datetime import datetime


def test_summary_positive_totals_and_signed_net(client, make_user, add_tx):
    user, account, headers = make_user()
    add_tx(account, 2000.0, datetime(2026, 3, 1, 9), merchant="Employer", category="Income")
    add_tx(account, -1500.0, datetime(2026, 3, 5), merchant="Landlord", category="Other")
    add_tx(account, -700.0, datetime(2026, 3, 10), merchant="Tesco", category="Groceries")
    add_tx(account, -999.0, datetime(2026, 4, 1), merchant="Tesco", category="Groceries")  # other month

    data = client.get("/transactions/summary", params={"month": 3, "year": 2026}, headers=headers).json()

    assert data["income"] == 2000.0
    assert data["spend"] == 2200.0
    assert data["net"] == -200.0
    assert data["by_category"][0] == {"category": "Other", "total": 1500.0, "count": 1}
    assert all(c["total"] > 0 for c in data["by_category"])


def test_summary_only_includes_own_transactions(client, make_user, add_tx):
    _, account_a, _ = make_user()
    _, _, headers_b = make_user()
    add_tx(account_a, -50.0, datetime(2026, 3, 5))
    data = client.get("/transactions/summary", params={"month": 3, "year": 2026}, headers=headers_b).json()
    assert data["spend"] == 0
