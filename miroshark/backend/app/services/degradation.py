"""Posture-B degradation taxonomy (ZERA-600).

Pure, dependency-free classification of *why* a token-bridge simulation cannot
yield a consensus, plus the specifically-actionable remediation for each case.
Kept side-effect-free so it is deterministically unit-testable (3(b)) and
shared by both the prep pipeline and the consensus endpoint.

Contract (CEO/CPO acceptance, ZERA-600):
  * every consensus-dependent response is HTTP 200, success=true, degraded=true,
    simulation_consensus=null — never a hang / 5xx / silent null;
  * `reason` is one of the enumerated codes below so callers (and judges) can
    tell degradation causes apart;
  * the OOM-killed-mid-debate case maps to ``simulation_incomplete_resource``
    with a remediation that names the fix (≥12 GB Docker memory), not "retry".
"""

from __future__ import annotations

from typing import Optional, Tuple

# Enumerated degradation reasons. Stable string codes — judges/automation key
# off these, so do not rename without updating the README contract.
NO_LLM_KEY = "no_llm_key"
GRAPH_UNSEEDED = "graph_unseeded"
MIROSHARK_UNREACHABLE = "miroshark_unreachable"
SIMULATION_INCOMPLETE_RESOURCE = "simulation_incomplete_resource"

REASONS = (
    NO_LLM_KEY,
    GRAPH_UNSEEDED,
    MIROSHARK_UNREACHABLE,
    SIMULATION_INCOMPLETE_RESOURCE,
)

REMEDIATION = {
    NO_LLM_KEY: (
        "MiroShark could not reach the LLM (missing / invalid / expired "
        "LLM_API_KEY — an expired or wrong key behaves exactly like no key, "
        "this is expected). Set a valid OpenAI-compatible LLM_API_KEY in the "
        "bags .env and re-run the documented command."
    ),
    GRAPH_UNSEEDED: (
        "Knowledge graph not populated. Recreate the stack with "
        "`docker compose down -v && docker compose up --build` so the "
        "empty-Neo4j synthetic seed step runs (no manual step required)."
    ),
    MIROSHARK_UNREACHABLE: (
        "MiroShark service is not reachable (down or restart-looping — often "
        "an out-of-memory restart loop). Increase Docker Desktop memory "
        "allocation to >=12 GB and re-run the documented command."
    ),
    SIMULATION_INCOMPLETE_RESOURCE: (
        "Simulation did not complete (likely insufficient Docker memory; "
        "MiroShark was OOM-killed mid-debate). Increase Docker Desktop memory "
        "allocation to >=12 GB and re-run the documented command."
    ),
}

# Sentinel prefix used to persist a machine reason inside the free-text
# SimulationState.error without changing the dataclass / its serialization.
_SENTINEL = "[zera600-reason="


def encode_reason(reason: str, message: str) -> str:
    """Embed a machine reason code in the human error string."""
    return f"{_SENTINEL}{reason}] {message}"


def decode_reason(error: Optional[str]) -> Optional[str]:
    """Extract a machine reason code from a persisted error string, if any."""
    if not error or _SENTINEL not in error:
        return None
    try:
        tag = error.split(_SENTINEL, 1)[1].split("]", 1)[0].strip()
        return tag if tag in REASONS else None
    except Exception:
        return None


def classify_prep_failure(error_text: Optional[str]) -> str:
    """Classify why `prepare_simulation` did not reach READY.

    Pure string heuristic over the raised/stored error. Order matters:
    graph-empty is the most specific, LLM/auth next, resource is the
    catch-all for "started but could not finish".
    """
    e = (error_text or "").lower()
    if not e:
        return SIMULATION_INCOMPLETE_RESOURCE
    if any(k in e for k in (
        "no matching entities", "graph is built", "0 edges",
        "not populated", "empty graph", "graph not populated",
    )):
        return GRAPH_UNSEEDED
    if any(k in e for k in (
        "api key", "api_key", "unauthorized", "401", "invalid api",
        "user not found", "llm", "openai", "openrouter", "auth",
        "connection", "connect", "timed out", "timeout",
        "rate limit", "429", "quota", "insufficient_quota",
    )):
        return NO_LLM_KEY
    return SIMULATION_INCOMPLETE_RESOURCE


def classify_degradation(
    status: str,
    error_text: Optional[str],
    num_actions: int,
    runner_alive: bool,
) -> Tuple[bool, Optional[str], str, str]:
    """Decide if a simulation is degraded and why.

    Returns ``(degraded, reason, message, remediation)``. ``degraded`` False
    means the sim is genuinely healthy/complete or still legitimately in
    progress and the caller should fall through to normal aggregation.

    Deterministic and side-effect free — this is the function 3(b) pins.
    """
    s = (status or "").lower()

    # Explicit terminal failure: trust the persisted/derived reason.
    if s in ("failed", "stopped"):
        reason = decode_reason(error_text) or classify_prep_failure(error_text)
        return True, reason, (error_text or "Simulation failed."), REMEDIATION[reason]

    # Completed: only degraded if it produced nothing at all (a "completed"
    # sim with zero actions never aggregated → resource/abort class).
    if s == "completed":
        if num_actions <= 0:
            return (
                True,
                SIMULATION_INCOMPLETE_RESOURCE,
                "Simulation reported complete but produced no agent actions.",
                REMEDIATION[SIMULATION_INCOMPLETE_RESOURCE],
            )
        return False, None, "", ""

    # In-flight states. The OOM-mid-debate signature: the sim was started
    # (running/ready/preparing) but its runner process is no longer alive and
    # it has not completed — i.e. it was killed, not finishing on its own.
    if s in ("running", "ready", "preparing", "created", "paused"):
        if not runner_alive and num_actions <= 0 and s in ("running", "ready"):
            return (
                True,
                SIMULATION_INCOMPLETE_RESOURCE,
                "Simulation was started but its runner is no longer alive and "
                "produced no actions — it was aborted mid-run (out-of-memory "
                "kill is the common cause on under-provisioned Docker).",
                REMEDIATION[SIMULATION_INCOMPLETE_RESOURCE],
            )
        # Genuinely still working — not degraded, just pending.
        return False, None, "", ""

    # Unknown state: fail safe to a structured degraded envelope rather than
    # ever letting the caller hang or 5xx.
    return (
        True,
        SIMULATION_INCOMPLETE_RESOURCE,
        f"Simulation in an unexpected state '{status}' with no consensus.",
        REMEDIATION[SIMULATION_INCOMPLETE_RESOURCE],
    )


def degraded_payload(simulation_id: str, status_str: str, reason: str,
                      message: str, remediation: str) -> dict:
    """The single canonical Posture-B envelope (HTTP 200, never null-silent)."""
    return {
        "success": True,
        "simulation_id": simulation_id,
        "status": status_str,
        "degraded": True,
        "reason": reason,
        "degraded_reason": message,
        "simulation_note": {
            "state": "degraded",
            "reason": reason,
            "message": message,
            "remediation": remediation,
        },
        "remediation": remediation,
        "rounds_completed": 0,
        "total_posts_analyzed": 0,
        "sentiment_distribution": {"bullish": 0, "bearish": 0, "neutral": 0},
        "top_arguments": {"bullish": [], "bearish": []},
        "belief_trajectory": [],
        "predicted_direction": "unavailable",
        "confidence": 0,
        "agent_attestations": [],
        "sim_root_did": None,
        "manifest": None,
        "manifest_signature": None,
        "simulation_consensus": None,
    }
