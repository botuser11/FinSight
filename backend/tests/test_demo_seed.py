from datetime import datetime, timedelta

from sqlalchemy import func

import seed_demo_data as seed
from models import AppMeta, Transaction
from tests.conftest import login


def test_demo_seeded_with_current_version_and_no_future_rows(client, db):
    account = seed._demo_account(db)
    assert db.get(AppMeta, seed.SEED_VERSION_KEY).value == str(seed.SEED_VERSION)
    latest = db.query(func.max(Transaction.timestamp)).filter(Transaction.account_id == account.id).scalar()
    assert latest <= datetime.utcnow()
    assert not seed.demo_needs_reseed(db, account)


def test_every_month_including_current_has_salary():
    now = datetime.utcnow()
    cat_map = {name: i for i, (name, _) in enumerate(seed.CATEGORIES)}
    rows = seed.generate_transactions(1, cat_map, now)
    salary_months = {
        (r["timestamp"].year, r["timestamp"].month) for r in rows if r["merchant_name"] == "Employer Payroll"
    }
    assert (now.year, now.month) in salary_months
    assert len(salary_months) == seed.MONTHS_OF_HISTORY
    assert all(r["timestamp"] <= now for r in rows)


def test_version_mismatch_triggers_reseed(client, db):
    db.merge(AppMeta(key=seed.SEED_VERSION_KEY, value="0"))
    db.commit()
    account = seed._demo_account(db)
    assert seed.demo_needs_reseed(db, account)
    assert seed.refresh_demo_if_stale(db) is True
    assert db.get(AppMeta, seed.SEED_VERSION_KEY).value == str(seed.SEED_VERSION)
    assert seed.refresh_demo_if_stale(db) is False


def test_stale_data_reseeded_on_demo_login(client, db):
    account = seed._demo_account(db)
    for tx in db.query(Transaction).filter(Transaction.account_id == account.id):
        tx.timestamp -= timedelta(days=5)
    db.commit()
    assert seed.demo_needs_reseed(db, account)

    login(client, "demo@finsight.app", "demo1234")

    db.expire_all()
    latest = db.query(func.max(Transaction.timestamp)).filter(Transaction.account_id == account.id).scalar()
    assert datetime.utcnow() - latest < timedelta(days=3)


def test_reseed_flags_only_the_planted_anomalies(client, db):
    seed.refresh_demo_if_stale(db)
    account = seed._demo_account(db)
    flagged = db.query(Transaction).filter(
        Transaction.account_id == account.id, Transaction.is_anomaly == True  # noqa: E712
    ).all()
    planted = {merchant for _, merchant, _, _ in seed.ANOMALIES}
    assert {t.merchant_name for t in flagged} <= planted
    assert 1 <= len(flagged) <= len(seed.ANOMALIES)


def test_demo_login_resets_sample_uncategorised_rows(client, db):
    account = seed._demo_account(db)
    names = [merchant for _, merchant, _ in seed.UNCATEGORISED]
    db.query(Transaction).filter(
        Transaction.account_id == account.id, Transaction.merchant_name.in_(names)
    ).update({"categorisation_source": "llm"}, synchronize_session=False)
    db.commit()

    login(client, "demo@finsight.app", "demo1234")

    db.expire_all()
    pending = db.query(Transaction).filter(
        Transaction.account_id == account.id, Transaction.categorisation_source == "pending"
    ).count()
    assert pending == len(seed.UNCATEGORISED)
