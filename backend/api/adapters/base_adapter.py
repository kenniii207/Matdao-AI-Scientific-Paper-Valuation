"""Abstract base adapter for scholarly API integrations."""

from __future__ import annotations

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping
from typing import Optional, TypeAlias

import httpx

from backend.core.rate_limiter import RateLimiter, exponential_backoff_delay
from backend.core.exceptions import AdapterError, RateLimitExceeded

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
JSONPrimitive: TypeAlias = str | int | float | bool | None
JSONValue: TypeAlias = JSONPrimitive | dict[str, "JSONValue"] | list["JSONValue"]
JSONObject: TypeAlias = dict[str, JSONValue]
QueryParams: TypeAlias = Mapping[str, str | int | float | bool | None]


class BaseAdapter(ABC):
    """All API adapters inherit from this. Provides rate limiting, retry, and origin_snippet capture."""

    def __init__(
        self,
        base_url: str,
        rate_limit: float,
        headers: Optional[dict[str, str]] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.rate_limiter = RateLimiter(requests_per_second=rate_limit)
        self.default_headers = headers or {}
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=self.default_headers,
                timeout=30.0,
            )
        return self._client

    async def _request(
        self,
        method: str,
        path: str,
        params: Optional[QueryParams] = None,
        json_body: Optional[JSONObject] = None,
    ) -> JSONObject:
        """Make an HTTP request with rate limiting and exponential backoff on 429."""
        client = await self._get_client()

        for attempt in range(MAX_RETRIES + 1):
            await self.rate_limiter.acquire()
            try:
                response = await client.request(
                    method, path, params=params, json=json_body
                )

                if response.status_code == 429:
                    if attempt < MAX_RETRIES:
                        delay = exponential_backoff_delay(attempt)
                        logger.warning(
                            "%s: 429 rate limited. Retry %d/%d in %.1fs",
                            self.__class__.__name__,
                            attempt + 1,
                            MAX_RETRIES,
                            delay,
                        )
                        await asyncio.sleep(delay)
                        continue
                    raise RateLimitExceeded(
                        f"{self.__class__.__name__}: rate limit exceeded after {MAX_RETRIES} retries"
                    )

                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict):
                    raise AdapterError(
                        f"{self.__class__.__name__}: expected JSON object response, got {type(payload).__name__}"
                    )
                return payload

            except httpx.HTTPStatusError as exc:
                raise AdapterError(
                    f"{self.__class__.__name__}: HTTP {exc.response.status_code} — {exc.response.text[:200]}"
                ) from exc
            except httpx.RequestError as exc:
                if attempt < MAX_RETRIES:
                    delay = exponential_backoff_delay(attempt)
                    logger.warning(
                        "%s: request error. Retry %d/%d in %.1fs: %s",
                        self.__class__.__name__,
                        attempt + 1,
                        MAX_RETRIES,
                        delay,
                        str(exc),
                    )
                    await asyncio.sleep(delay)
                    continue
                raise AdapterError(
                    f"{self.__class__.__name__}: request failed — {exc}"
                ) from exc

        raise AdapterError(f"{self.__class__.__name__}: all retries exhausted")

    def _capture_snippet(self, data: JSONObject, max_length: int = 500) -> str:
        """Capture origin_snippet from API response for auditability."""
        raw = json.dumps(data, default=str)
        return raw[:max_length]

    @staticmethod
    def _bounded(value: int, minimum: int = 1, maximum: int = 10) -> int:
        """Bound caller-provided limits to safe API ranges."""
        return max(minimum, min(value, maximum))

    @staticmethod
    def _normalize_items(
        items: list[JSONValue], transform: Callable[[JSONObject], JSONObject]
    ) -> list[JSONObject]:
        """Normalize a list of dict payload items while skipping non-object entries."""
        normalized: list[JSONObject] = []
        for item in items:
            if isinstance(item, dict):
                normalized.append(transform(item))
        return normalized

    @abstractmethod
    async def fetch(self, identifier: str) -> JSONObject:
        """Fetch data for a given identifier (DOI, title, etc.)."""

    async def health_check(self) -> bool:
        """Check if the upstream API is reachable."""
        try:
            client = await self._get_client()
            response = await client.get("/")
            return response.status_code < 500
        except httpx.RequestError:
            return False

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
