"""Token-bucket rate limiter with exponential backoff for API adapters."""

from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass, field


@dataclass
class RateLimiter:
    """Token-bucket rate limiter. Thread/async safe via asyncio.Lock."""

    requests_per_second: float
    _tokens: float = field(init=False)
    _last_refill: float = field(init=False)
    _lock: asyncio.Lock = field(init=False, default_factory=asyncio.Lock)

    def __post_init__(self):
        self._tokens = self.requests_per_second
        self._last_refill = time.monotonic()

    async def acquire(self):
        """Wait until a token is available. Blocks if bucket is empty."""
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_refill
            self._tokens = min(
                self.requests_per_second,
                self._tokens + elapsed * self.requests_per_second,
            )
            self._last_refill = now

            if self._tokens < 1.0:
                wait = (1.0 - self._tokens) / self.requests_per_second
                await asyncio.sleep(wait)
                self._tokens = 0.0
                self._last_refill = time.monotonic()
            else:
                self._tokens -= 1.0


def exponential_backoff_delay(
    attempt: int,
    base_seconds: float = 1.0,
    max_seconds: float = 60.0,
    jitter: bool = True,
) -> float:
    """Calculate delay for exponential backoff with optional jitter."""
    delay = min(base_seconds * (2 ** attempt), max_seconds)
    if jitter:
        delay *= 0.5 + random.random()
    return delay
