"""
Bags.fm token launch data client.

Fetches token launches, pool info, lifetime fees, and trade quotes
from the Bags.fm public API v2.

Requires BAGS_FM_API_KEY env var. Bags public API now rejects all
unauthenticated requests with 401 (verified 2026-04-17), including
the token-launch/feed endpoint that was previously anonymous.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://public-api-v2.bags.fm/api/v1"

MAX_RETRIES = 3
BACKOFF_BASE = 1.0
DEFAULT_CACHE_TTL = 30


class _Cache:
    def __init__(self, ttl: int = DEFAULT_CACHE_TTL):
        self._ttl = ttl
        self._store: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        ts, val = entry
        if time.monotonic() - ts > self._ttl:
            del self._store[key]
            return None
        return val

    def set(self, key: str, val: Any) -> None:
        self._store[key] = (time.monotonic(), val)

    def clear(self) -> None:
        self._store.clear()


class BagsClient:
    """Read-only Bags.fm data client for token launches and analytics.

    Args:
        api_key: Bags.fm API key. Falls back to BAGS_FM_API_KEY env var.
        cache_ttl: Cache lifetime in seconds. Set to 0 to disable.
    """

    def __init__(
        self,
        api_key: str | None = None,
        cache_ttl: int = DEFAULT_CACHE_TTL,
    ):
        self._api_key = api_key or os.environ.get("BAGS_FM_API_KEY")
        self._cache = _Cache(ttl=cache_ttl)
        self._http = httpx.Client(
            base_url=BASE_URL,
            timeout=15.0,
            headers=self._build_headers(),
        )

    @property
    def has_api_key(self) -> bool:
        return bool(self._api_key)

    def _build_headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self._api_key:
            headers["x-api-key"] = self._api_key
        return headers

    def _request(self, method: str, path: str, **kwargs) -> Any:
        last_exc = None
        for attempt in range(MAX_RETRIES):
            try:
                resp = self._http.request(method, path, **kwargs)
                resp.raise_for_status()
                data = resp.json()
                if isinstance(data, dict) and data.get("success") is False:
                    raise BagsAPIError(data.get("error", "Unknown error"))
                if isinstance(data, dict) and "response" in data:
                    return data["response"]
                return data
            except (httpx.HTTPStatusError, httpx.TransportError, BagsAPIError) as exc:
                last_exc = exc
                if isinstance(exc, httpx.HTTPStatusError) and 400 <= exc.response.status_code < 500:
                    raise   # client errors (404, 401, 403, etc.) are final — don't retry
                wait = BACKOFF_BASE * (2 ** attempt)
                logger.warning("Bags.fm attempt %d/%d failed: %s", attempt + 1, MAX_RETRIES, exc)
                time.sleep(wait)
        raise last_exc  # type: ignore[misc]

    def _get(self, path: str, params: dict | None = None) -> Any:
        return self._request("GET", path, params=params)

    def fetch_launch_feed(self, limit: int = 100) -> list[dict]:
        """Fetch recent token launches. Requires BAGS_FM_API_KEY (Bags removed anonymous access)."""
        cache_key = f"feed:{limit}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        result = self._get("/token-launch/feed")
        if isinstance(result, list):
            result = result[:limit]
        self._cache.set(cache_key, result)
        return result

    def fetch_pool_info(self, token_mint: str) -> dict | None:
        """Fetch pool info for a token (requires auth)."""
        if not self._api_key:
            return None
        cache_key = f"pool:{token_mint}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        try:
            result = self._get("/token-launch/pool-info", params={"tokenMint": token_mint})
            self._cache.set(cache_key, result)
            return result
        except Exception as exc:
            logger.warning("Pool info fetch failed for %s: %s", token_mint, exc)
            return None

    def fetch_lifetime_fees(self, token_mint: str) -> str | None:
        """Fetch total lifetime fees for a token (requires auth)."""
        if not self._api_key:
            return None
        cache_key = f"fees:{token_mint}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        try:
            result = self._get("/token-launch/lifetime-fees", params={"tokenMint": token_mint})
            self._cache.set(cache_key, result)
            return result
        except Exception as exc:
            logger.warning("Lifetime fees fetch failed for %s: %s", token_mint, exc)
            return None

    def fetch_creators(self, token_mint: str) -> list[dict] | None:
        """Fetch creator info for a token (requires auth)."""
        if not self._api_key:
            return None
        cache_key = f"creators:{token_mint}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        try:
            result = self._get("/token-launch/creator/v3", params={"tokenMint": token_mint})
            self._cache.set(cache_key, result)
            return result
        except Exception as exc:
            logger.warning("Creator fetch failed for %s: %s", token_mint, exc)
            return None

    def fetch_trade_quote(
        self,
        input_mint: str,
        output_mint: str,
        in_amount: str,
        slippage_bps: int = 100,
    ) -> dict | None:
        """Get a trade quote (requires auth)."""
        if not self._api_key:
            return None
        try:
            return self._get("/trade/quote", params={
                "inputMint": input_mint,
                "outputMint": output_mint,
                "inAmount": in_amount,
                "slippageBps": slippage_bps,
            })
        except Exception as exc:
            logger.warning("Trade quote failed: %s", exc)
            return None

    def clear_cache(self) -> None:
        self._cache.clear()

    def close(self) -> None:
        self._http.close()


class BagsAPIError(Exception):
    pass
