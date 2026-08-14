"""Small process-wide rate limiter for deployment abuse control."""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from threading import Lock
from time import monotonic


class SlidingWindowRateLimiter:
    """Bound accepted events within a moving time window without user identifiers."""

    def __init__(
        self,
        limit: int,
        *,
        window_seconds: float = 60.0,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        if limit < 0:
            raise ValueError("Rate limit must be zero (disabled) or a positive integer.")
        if window_seconds <= 0:
            raise ValueError("Rate-limit window must be positive.")
        self.limit = limit
        self.window_seconds = window_seconds
        self._clock = clock
        self._accepted: deque[float] = deque()
        self._lock = Lock()

    def allow(self) -> bool:
        """Return whether one event may proceed and consume budget when accepted."""
        if self.limit == 0:
            return True
        now = self._clock()
        cutoff = now - self.window_seconds
        with self._lock:
            while self._accepted and self._accepted[0] <= cutoff:
                self._accepted.popleft()
            if len(self._accepted) >= self.limit:
                return False
            self._accepted.append(now)
            return True
