from slowapi import Limiter
from slowapi.util import get_ipaddr

# Keyed on the first X-Forwarded-For hop (the client IP behind Render's proxy),
# falling back to the socket address. In-memory storage: fine for one worker.
limiter = Limiter(key_func=get_ipaddr)
