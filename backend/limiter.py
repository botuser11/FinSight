import os

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

ON_RENDER = bool(os.getenv("RENDER"))  # Render sets RENDER=true on every service


def client_ip(request: Request) -> str:
    """Client IP for rate limiting that a caller can't choose.

    Render puts Cloudflare and then its own load balancer in front of the app,
    so the socket address is always an internal proxy. Render's proxy does NOT
    strip a client-supplied X-Forwarded-For; it appends to it, giving
    "<anything the client sent>, <real client>, <Cloudflare edge>, <Render 10.x>".
    The leftmost entry (what slowapi's get_ipaddr uses) is therefore spoofable.

    What the edge does set authoritatively (reported behaviour of Render's edge,
    see github.com/johnbeynon/header-test and Render's DDoS article):
      - True-Client-IP: overwritten with the real client IP if the client sends one
      - CF-Connecting-IP: set by Cloudflare; a client-supplied one is rejected (403)
    so prefer those, then fall back to counting hops from the right of
    X-Forwarded-For (client = 3rd from the right), which only trusts entries
    our proxies appended.

    Off Render there is no trusted proxy, so headers are ignored and the
    socket address is used.
    """
    if ON_RENDER:
        headers = request.headers
        for name in ("true-client-ip", "cf-connecting-ip"):
            value = headers.get(name, "").strip()
            if value:
                return value
        hops = [h.strip() for h in headers.get("x-forwarded-for", "").split(",") if h.strip()]
        if len(hops) >= 3:
            return hops[-3]
    return get_remote_address(request)


# In-memory storage: fine for a single worker
limiter = Limiter(key_func=client_ip)
