from __future__ import annotations

import pytest

from skillpulse.api.rate_limit import SlidingWindowRateLimiter


def test_sliding_window_releases_budget_after_window() -> None:
    now = [100.0]
    limiter = SlidingWindowRateLimiter(2, window_seconds=60, clock=lambda: now[0])

    assert limiter.allow()
    assert limiter.allow()
    assert not limiter.allow()
    now[0] = 160.0
    assert limiter.allow()


def test_zero_disables_limit_without_collecting_identifiers() -> None:
    limiter = SlidingWindowRateLimiter(0)
    assert all(limiter.allow() for _ in range(100))


@pytest.mark.parametrize("limit,window", [(-1, 60), (1, 0)])
def test_invalid_configuration_fails_closed(limit: int, window: float) -> None:
    with pytest.raises(ValueError):
        SlidingWindowRateLimiter(limit, window_seconds=window)
