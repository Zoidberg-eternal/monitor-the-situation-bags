"""
MiroShark simulation client.

Triggers social simulations from token data and retrieves consensus results
via the MiroShark API bridge endpoints.

Env: MIROSHARK_URL (default http://localhost:5000)
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

DEFAULT_URL = "http://localhost:5001"
MAX_RETRIES = 3
BACKOFF_BASE = 1.0
REQUEST_TIMEOUT = 30.0


class MiroSharkClient:
    """Client for the MiroShark simulation bridge API.

    Args:
        base_url: MiroShark API base URL. Falls back to MIROSHARK_URL env var.
        timeout: Request timeout in seconds.
    """

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = REQUEST_TIMEOUT,
    ):
        self._base_url = (base_url or os.environ.get("MIROSHARK_URL", DEFAULT_URL)).rstrip("/")
        self._timeout = timeout
        self._available: bool | None = None

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict | None:
        """Make an HTTP request with retry logic and graceful fallback."""
        url = f"{self._base_url}{path}"
        import asyncio

        for attempt in range(MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    resp = await client.request(method, url, **kwargs)
                    resp.raise_for_status()
                    self._available = True
                    return resp.json()
            except httpx.ConnectError:
                if self._available is not False:
                    logger.warning("MiroShark unavailable at %s", self._base_url)
                    self._available = False
                return None
            except httpx.HTTPStatusError as e:
                logger.error("MiroShark %s %s returned %s: %s", method, path, e.response.status_code, e.response.text[:200])
                return None
            except (httpx.TimeoutException, httpx.RequestError) as e:
                wait = BACKOFF_BASE * (2 ** attempt)
                logger.warning("MiroShark request failed (attempt %d/%d): %s — retrying in %.1fs", attempt + 1, MAX_RETRIES, e, wait)
                await asyncio.sleep(wait)

        logger.error("MiroShark request failed after %d attempts: %s %s", MAX_RETRIES, method, path)
        return None

    @property
    def is_available(self) -> bool | None:
        """Last known availability. None if never checked."""
        return self._available

    async def health_check(self) -> bool:
        """Check if MiroShark is reachable."""
        result = await self._request("GET", "/health")
        return result is not None and result.get("status") == "ok"

    async def trigger_simulation(self, token_data: dict) -> str | None:
        """Trigger a MiroShark simulation from token metadata.

        Args:
            token_data: Token metadata dict with keys:
                name, ticker, description, team_info, market_data, market_context

        Returns:
            simulation_id if successful, None if MiroShark unavailable.
        """
        result = await self._request("POST", "/api/simulation/from-token", json=token_data)
        if result and result.get("success"):
            sim_id = result["simulation_id"]
            logger.info("MiroShark simulation triggered: %s", sim_id)
            return sim_id
        if result:
            logger.error("MiroShark trigger failed: %s", result.get("error", "unknown"))
        return None

    async def get_status(self, simulation_id: str) -> dict | None:
        """Get simulation status and progress.

        Returns:
            Simulation state dict or None if unavailable.
        """
        result = await self._request("GET", f"/api/simulation/{simulation_id}")
        if result and result.get("success"):
            return result.get("data", result)
        return None

    async def get_consensus(self, simulation_id: str) -> dict | None:
        """Get aggregated consensus from a simulation.

        Returns:
            Consensus dict with sentiment_distribution, predicted_direction,
            confidence, belief_trajectory, etc. None if unavailable.
        """
        result = await self._request("GET", f"/api/simulation/{simulation_id}/consensus")
        if result and result.get("success"):
            return {
                "simulation_id": result.get("simulation_id"),
                "status": result.get("status"),
                "rounds_completed": result.get("rounds_completed", 0),
                "total_posts_analyzed": result.get("total_posts_analyzed", 0),
                "sentiment_distribution": result.get("sentiment_distribution", {}),
                "top_arguments": result.get("top_arguments", {}),
                "belief_trajectory": result.get("belief_trajectory", []),
                "predicted_direction": result.get("predicted_direction", "unknown"),
                "confidence": result.get("confidence", 0),
                # KYA (Know Your Agent) attestations — pass through as-is so
                # downstream consumers can verify each agent's contribution
                # and the sim-root manifest signature against MiroShark's
                # /api/verify endpoint.
                "agent_attestations": result.get("agent_attestations", []),
                "sim_root_did": result.get("sim_root_did"),
                "manifest": result.get("manifest"),
                "manifest_signature": result.get("manifest_signature"),
            }
        return None
