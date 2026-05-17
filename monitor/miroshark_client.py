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
# Posture-B (ZERA-600): consensus/status reads must yield a structured answer
# within a few seconds even if MiroShark is OOM-killed / restart-looping —
# "never a hang" is only enforceable with an explicit bound.
BOUNDED_TIMEOUT = 6.0

# Enumerated degradation reasons — must match MiroShark's
# app/services/degradation.py so a judge sees one stable taxonomy.
REASON_NO_LLM_KEY = "no_llm_key"
REASON_GRAPH_UNSEEDED = "graph_unseeded"
REASON_MIROSHARK_UNREACHABLE = "miroshark_unreachable"
REASON_SIM_INCOMPLETE_RESOURCE = "simulation_incomplete_resource"

_UNREACHABLE_REMEDIATION = (
    "MiroShark is not reachable (down or restart-looping — commonly an "
    "out-of-memory restart loop on under-provisioned Docker). Increase "
    "Docker Desktop memory allocation to >=12 GB and re-run the documented "
    "command."
)


def unreachable_envelope(simulation_id: str | None = None) -> dict:
    """Synthetic Posture-B envelope when MiroShark itself cannot be reached.

    Never None — callers must always get a structured, non-fatal answer.
    """
    return {
        "simulation_id": simulation_id,
        "status": "unreachable",
        "degraded": True,
        "reason": REASON_MIROSHARK_UNREACHABLE,
        "degraded_reason": "MiroShark service did not respond within the bound.",
        "simulation_note": {
            "state": "degraded",
            "reason": REASON_MIROSHARK_UNREACHABLE,
            "message": "MiroShark service did not respond within the bound.",
            "remediation": _UNREACHABLE_REMEDIATION,
        },
        "remediation": _UNREACHABLE_REMEDIATION,
        "sentiment_distribution": {},
        "top_arguments": {},
        "belief_trajectory": [],
        "predicted_direction": "unavailable",
        "confidence": 0,
        "agent_attestations": [],
        "sim_root_did": None,
        "manifest": None,
        "manifest_signature": None,
        "simulation_consensus": None,
    }


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

    async def _request(self, method: str, path: str, bounded: bool = False,
                       **kwargs: Any) -> dict | None:
        """HTTP request with retry + graceful fallback.

        ``bounded=True``: a single attempt with a short timeout and no
        backoff sleeps — used for consensus/status reads so an OOM-killed or
        restart-looping MiroShark returns control within a few seconds
        instead of hanging through the full retry/backoff budget.
        """
        url = f"{self._base_url}{path}"
        import asyncio

        attempts = 1 if bounded else MAX_RETRIES
        timeout = BOUNDED_TIMEOUT if bounded else self._timeout

        for attempt in range(attempts):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
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
                if bounded:
                    logger.warning("MiroShark bounded request timed out/failed: %s %s (%s)", method, path, e)
                    return None
                wait = BACKOFF_BASE * (2 ** attempt)
                logger.warning("MiroShark request failed (attempt %d/%d): %s — retrying in %.1fs", attempt + 1, MAX_RETRIES, e, wait)
                await asyncio.sleep(wait)

        logger.error("MiroShark request failed after %d attempts: %s %s", attempts, method, path)
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
        result = await self._request(
            "GET", f"/api/simulation/{simulation_id}/consensus", bounded=True)
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
                # Posture-B passthrough (ZERA-600): keep the enumerated reason
                # + remediation so monitor never collapses it to a bare null.
                "degraded": result.get("degraded", False),
                "reason": result.get("reason"),
                "degraded_reason": result.get("degraded_reason"),
                "simulation_note": result.get("simulation_note"),
                "remediation": result.get("remediation"),
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

    async def consensus_envelope(self, simulation_id: str) -> dict:
        """Posture-B: ALWAYS returns a structured dict, never None.

        Healthy/degraded consensus from MiroShark when reachable; a
        synthetic ``miroshark_unreachable`` envelope (within the bounded
        timeout) when it is down or restart-looping. Guarantees the caller
        can always return HTTP 200 with an enumerated reason.
        """
        result = await self.get_consensus(simulation_id)
        if result is None:
            return unreachable_envelope(simulation_id)
        return result
