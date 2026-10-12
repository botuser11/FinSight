from datetime import datetime, timedelta

from anomaly_detector import detect_anomalies, is_anomalous
from insights import detect_price_increases, detect_subscriptions, subscription_frequency
from models import Transaction


def test_is_anomalous_needs_a_real_spike():
    fares = [2.8, 3.1, 4.0, 2.5, 5.9, 3.3, 4.4]
    assert not is_anomalous(5.9, fares)
    assert is_anomalous(250.0, [50, 60, 45, 70, 55, 65, 52, 250])
    assert not is_anomalous(17.99, [15.99] * 8 + [17.99])  # a small price rise is not an anomaly


def test_anomalies_are_per_merchant(client, make_user, add_tx, db):
    user, account, _ = make_user()
    start = datetime(2026, 1, 1)
    # Cheap fares and pricier fuel share the Transport category but must not be compared
    for i in range(20):
        add_tx(account, -3.0 - (i % 3) * 0.5, start + timedelta(days=i), merchant="TfL", category="Transport")
    for i in range(8):
        add_tx(account, -55.0 - i, start + timedelta(days=3 * i), merchant="Shell", category="Transport")
    spike = add_tx(account, -240.0, start + timedelta(days=30), merchant="Shell", category="Transport")

    result = detect_anomalies(db, user.id)

    flagged = db.query(Transaction).filter(
        Transaction.account_id == account.id, Transaction.is_anomaly == True  # noqa: E712
    ).all()
    assert [t.id for t in flagged] == [spike.id]
    assert result["flagged"] == 1
    assert "Shell" in flagged[0].anomaly_reason


def test_merchant_with_short_history_is_never_flagged(client, make_user, add_tx, db):
    user, account, _ = make_user()
    for i, amount in enumerate([10, 12, 11, 500]):
        add_tx(account, -amount, datetime(2026, 1, 1) + timedelta(days=i), merchant="NewShop")
    assert detect_anomalies(db, user.id)["flagged"] == 0


def test_subscription_frequency_rules():
    monthly = [datetime(2026, m, 3) for m in range(1, 7)]
    assert subscription_frequency(monthly, [9.99] * 6) == "monthly"
    weekly = [datetime(2026, 1, 1) + timedelta(days=7 * i) for i in range(5)]
    assert subscription_frequency(weekly, [5.0] * 5) == "weekly"
    assert subscription_frequency(monthly[:2], [9.99] * 2) is None  # too few
    assert subscription_frequency(monthly, [40, 75, 52, 61, 44, 70]) is None  # unstable amount
    irregular = [datetime(2026, 1, d) for d in (1, 4, 19, 22)]
    assert subscription_frequency(irregular, [9.99] * 4) is None


def test_fuel_is_not_a_subscription_but_netflix_is(client, make_user, add_tx, db):
    user, account, _ = make_user()
    for m in range(1, 8):
        price = 15.99 if m < 5 else 17.99
        add_tx(account, -price, datetime(2026, m, 2, 10), merchant="Netflix", category="Subscriptions")
        add_tx(account, -48.0, datetime(2026, m, 3 + (m * 7) % 20), merchant="Shell", category="Transport")
        add_tx(account, -61.0, datetime(2026, m, 25), merchant="Shell", category="Transport")

    subs = {s["merchant"]: s for s in detect_subscriptions(db, user.id)}
    assert set(subs) == {"Netflix"}
    assert subs["Netflix"]["frequency"] == "monthly"

    alerts = detect_price_increases(db, user.id)
    assert [(a["merchant"], a["increase_pct"]) for a in alerts] == [("Netflix", 12.5)]
