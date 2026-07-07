"""Simple in-memory rate limiter for auth endpoints.

Sliding-window per key (e.g. IP or email). Suitable for single-instance
deployments. For multi-instance, swap for Redis-backed limiting.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock


class RateLimiter:
    def __init__(self, max_attempts: int, window_seconds: int):
        self.max_attempts = max_attempts
        self.window = window_seconds
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str) -> bool:
        """Return True if allowed, False if rate-limited. Records the attempt."""
        now = time.time()
        with self._lock:
            dq = self._hits[key]
            # Evict old entries
            while dq and dq[0] < now - self.window:
                dq.popleft()
            if len(dq) >= self.max_attempts:
                return False
            dq.append(now)
            return True

    def reset(self, key: str) -> None:
        """Clear attempts for a key (e.g. after successful login)."""
        with self._lock:
            self._hits.pop(key, None)

    def retry_after(self, key: str) -> int:
        """Seconds until the oldest attempt expires."""
        with self._lock:
            dq = self._hits.get(key)
            if not dq:
                return 0
            return max(0, int(dq[0] + self.window - time.time()))


# Login: 5 attempts per 5 minutes per IP+email
login_limiter = RateLimiter(max_attempts=5, window_seconds=300)
# Register: 3 accounts per hour per IP
register_limiter = RateLimiter(max_attempts=3, window_seconds=3600)
