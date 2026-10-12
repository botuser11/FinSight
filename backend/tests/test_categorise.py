from datetime import datetime

import pytest

import categoriser
from routers import transactions as tx_router


@pytest.fixture
def fake_llm(monkeypatch):
    calls = []

    def _fake(merchants):
        calls.append(list(merchants))
        return {m: "Dining" for m in merchants}

    monkeypatch.setattr(tx_router, "OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(tx_router, "llm_categorise_batch", _fake)
    return calls


def _pending(add_tx, account, merchants):
    for i, merchant in enumerate(merchants):
        add_tx(account, -10.0 - i, datetime(2026, 2, 1 + i), merchant=merchant, category=None, source="pending")


def test_rules_without_llm_mark_unknowns_other(client, make_user, add_tx):
    _, account, headers = make_user()
    _pending(add_tx, account, ["Tesco Express", "Mystery Merchant"])
    data = client.post("/transactions/categorise", headers=headers).json()
    assert data["by_source"] == {"rule": 1, "llm": 0, "cache": 0, "other": 1}
    assert data["pending"] == 0


def test_llm_batches_and_caches_by_merchant(client, make_user, add_tx, fake_llm, monkeypatch):
    monkeypatch.setattr(tx_router, "LLM_BATCH_SIZE", 2)
    _, account, headers = make_user()
    _pending(add_tx, account, ["Cafe Nero", "Zz Bistro A", "Zz Bistro B", "Zz Bistro C", "Zz Bistro A"])

    data = client.post("/transactions/categorise", params={"use_llm": True}, headers=headers).json()

    assert data["by_source"]["rule"] == 1  # "cafe" matches a rule
    assert data["by_source"]["llm"] == 4
    assert [len(batch) for batch in fake_llm] == [2, 1]  # 3 unique unknown merchants, batches of 2

    # The same merchant for another user comes from the cache: no new LLM call
    _, account2, headers2 = make_user()
    _pending(add_tx, account2, ["Zz Bistro B"])
    data2 = client.post("/transactions/categorise", params={"use_llm": True}, headers=headers2).json()
    assert data2["by_source"]["cache"] == 1
    assert len(fake_llm) == 2


def test_daily_cap_leaves_rest_pending(client, make_user, add_tx, fake_llm, monkeypatch):
    monkeypatch.setattr(tx_router, "LLM_BATCH_SIZE", 1)
    monkeypatch.setattr(tx_router, "LLM_DAILY_CALL_LIMIT", 2)
    _, account, headers = make_user()
    _pending(add_tx, account, ["Xx Alpha", "Xx Beta", "Xx Gamma"])

    data = client.post("/transactions/categorise", params={"use_llm": True}, headers=headers).json()

    assert data["llm"]["status"] == "limit_reached"
    assert data["categorised"] == 2
    assert data["pending"] == 1


def test_llm_failure_falls_back_and_keeps_pending(client, make_user, add_tx, monkeypatch):
    monkeypatch.setattr(tx_router, "OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(tx_router, "llm_categorise_batch", lambda merchants: None)
    _, account, headers = make_user()
    _pending(add_tx, account, ["Sainsbury's Local", "Ww Unknown"])

    data = client.post("/transactions/categorise", params={"use_llm": True}, headers=headers).json()

    assert data["llm"]["status"] == "failed"
    assert data["by_source"]["rule"] == 1
    assert data["pending"] == 1


def test_llm_response_parsing(monkeypatch):
    class Resp:
        status_code = 200

        def json(self):
            content = '```json\n{"categories": {"1": "Dining", "2": "Banana"}}\n```'
            return {"choices": [{"message": {"content": content}}]}

    monkeypatch.setattr(categoriser, "OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(categoriser.httpx, "post", lambda *a, **k: Resp())
    assert categoriser.llm_categorise_batch(["pret", "odd shop"]) == {"pret": "Dining", "odd shop": "Other"}
