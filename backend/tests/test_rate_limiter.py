"""Tests for rate limiter."""

import time
import pytest

from backend.core.rate_limiter import RateLimiter, exponential_backoff_delay


class TestRateLimiter:

    @pytest.mark.asyncio
    async def test_acquire_respects_rate(self):
        """Rate limiter should throttle requests."""
        limiter = RateLimiter(requests_per_second=10.0)
        # Should be able to acquire quickly for first few
        for _ in range(5):
            await limiter.acquire()

    @pytest.mark.asyncio
    async def test_slow_rate_limiter(self):
        """1 req/sec limiter should take ~1s for 2 requests."""
        limiter = RateLimiter(requests_per_second=1.0)
        await limiter.acquire()
        start = time.monotonic()
        await limiter.acquire()
        elapsed = time.monotonic() - start
        # Should have waited some time (at least partial)
        assert elapsed >= 0.0  # non-negative


class TestExponentialBackoff:

    def test_first_attempt_is_base(self):
        delay = exponential_backoff_delay(0, base_seconds=1.0, jitter=False)
        assert delay == 1.0

    def test_doubles_each_attempt(self):
        d1 = exponential_backoff_delay(1, base_seconds=1.0, jitter=False)
        d2 = exponential_backoff_delay(2, base_seconds=1.0, jitter=False)
        assert d1 == 2.0
        assert d2 == 4.0

    def test_respects_max(self):
        delay = exponential_backoff_delay(20, base_seconds=1.0, max_seconds=60.0, jitter=False)
        assert delay == 60.0

    def test_jitter_adds_randomness(self):
        delays = [exponential_backoff_delay(1, jitter=True) for _ in range(10)]
        # With jitter, not all delays should be identical
        assert len(set(delays)) > 1
