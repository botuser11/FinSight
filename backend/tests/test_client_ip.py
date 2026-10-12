from starlette.requests import Request

import limiter


def _request(headers):
    return Request({
        "type": "http",
        "headers": [(k.encode(), v.encode()) for k, v in headers.items()],
        "client": ("10.0.0.5", 1234),
    })


def test_off_render_ignores_forwarding_headers(monkeypatch):
    monkeypatch.setattr(limiter, "ON_RENDER", False)
    assert limiter.client_ip(_request({"x-forwarded-for": "1.2.3.4", "true-client-ip": "1.2.3.4"})) == "10.0.0.5"


def test_on_render_prefers_edge_set_header(monkeypatch):
    monkeypatch.setattr(limiter, "ON_RENDER", True)
    req = _request({"true-client-ip": "81.0.0.1", "x-forwarded-for": "6.6.6.6, 81.0.0.1, 172.71.0.1, 10.1.1.1"})
    assert limiter.client_ip(req) == "81.0.0.1"


def test_on_render_spoofed_leftmost_forwarded_for_is_ignored(monkeypatch):
    monkeypatch.setattr(limiter, "ON_RENDER", True)
    req = _request({"x-forwarded-for": "6.6.6.6, 81.0.0.1, 172.71.0.1, 10.1.1.1"})
    assert limiter.client_ip(req) == "81.0.0.1"
