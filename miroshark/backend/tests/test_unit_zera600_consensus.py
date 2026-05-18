"""ZERA-600 3(b): deterministic, RAM-independent proof that the
multi-agent-debate -> consensus *aggregation* path produces a NON-NULL
result, and that Posture-B degradation is correctly enumerated.

No LLM, no Neo4j, no network, no Docker. The LLM is "stubbed" by feeding
the aggregation the exact artifact a finished debate leaves behind — agent
actions (posts) — and asserting the real aggregation in
``token_bridge.get_consensus`` turns rounds into a non-null consensus.

This pins the single thing the CEO/CPO rider exists to de-risk: that
rounds -> non-null aggregation has no latent bug analogous to the
``sim_id`` UnboundLocalError that the clean-clone bar caught earlier.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from flask import Flask

_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from app.api import token_bridge  # noqa: E402
from app.services import degradation  # noqa: E402
from app.services.simulation_manager import SimulationStatus  # noqa: E402


# --------------------------- test doubles --------------------------------

class _FakeAction:
    def __init__(self, round_num, content, agent_id, agent_name):
        self._d = {
            "round_num": round_num,
            "action_type": "CREATE_POST",
            "result": content,
            "action_args": {"content": content},
            "agent_id": agent_id,
            "agent_name": agent_name,
            "timestamp": "2026-05-17T00:00:00Z",
        }

    def to_dict(self):
        return self._d


class _FakeState:
    def __init__(self, status, error=None):
        self.status = status
        self.error = error


class _FakeManager:
    """Stands in for SimulationManager; returns a preset state."""
    _state = None

    def __init__(self, *a, **k):
        pass

    def get_simulation(self, sim_id):
        return type(self)._state


def _synthetic_debate():
    """A finished 3-round debate: clearly bullish-leaning, deterministic."""
    return [
        _FakeAction(1, "I will buy this, strong bullish momentum, moon",  "a1", "Momentum Mia"),
        _FakeAction(1, "This looks like a rug, sell, bearish risk",        "a2", "Skeptic Sasha"),
        _FakeAction(2, "Accumulating — undervalued, long-term upside",     "a1", "Momentum Mia"),
        _FakeAction(2, "Neutral, watching liquidity before deciding",     "a3", "Quant Quinn"),
        _FakeAction(3, "Still bullish, buy the dip, growth ahead",        "a1", "Momentum Mia"),
        _FakeAction(3, "Bearish — overvalued, I will avoid",              "a2", "Skeptic Sasha"),
    ]


@pytest.fixture
def client(monkeypatch):
    app = Flask(__name__)
    app.register_blueprint(token_bridge.token_bridge_bp, url_prefix="/api/simulation")
    # Stub everything external: manager state, action store, keyring.
    monkeypatch.setattr(token_bridge, "SimulationManager", _FakeManager)
    monkeypatch.setattr(
        token_bridge.SimulationRunner, "get_actions",
        classmethod(lambda cls, simulation_id, limit=10000: _synthetic_debate()),
    )
    monkeypatch.setattr(token_bridge.SimulationRunner, "_processes", {}, raising=False)
    monkeypatch.setattr(token_bridge.SimulationKeyring, "lookup",
                        staticmethod(lambda sim_id: None))
    return app.test_client()


# --------------------------- 3(b) core: non-null aggregation --------------

def test_completed_debate_yields_non_null_consensus(client):
    _FakeManager._state = _FakeState(SimulationStatus.COMPLETED)
    resp = client.get("/api/simulation/sim_test/consensus")
    assert resp.status_code == 200
    body = resp.get_json()

    # The headline showcase must be NON-NULL and internally consistent.
    assert body["success"] is True
    assert body.get("degraded") in (False, None), "healthy debate must not degrade"
    sd = body["sentiment_distribution"]
    assert sd and abs(sum(sd.values()) - 1.0) < 1e-6, sd
    assert body["total_posts_analyzed"] == 6
    assert body["rounds_completed"] == 3
    assert body["predicted_direction"] in (
        "bullish", "cautiously_bullish", "bearish", "cautiously_bearish", "neutral")
    assert body["predicted_direction"] != "unavailable"
    assert body["confidence"] > 0
    assert len(body["belief_trajectory"]) == 3
    # Bullish-leaning debate -> bullish-side direction (deterministic).
    assert "bull" in body["predicted_direction"]
    # Manifest present (signed-or-not, but structurally non-null).
    assert body["manifest"] is not None
    assert body["manifest"]["total_posts_analyzed"] == 6


# --------------------------- Posture-B enumeration ------------------------

def test_classify_oom_mid_sim_is_resource_incomplete():
    # Sim was started (running) but runner is dead and produced nothing:
    # the OOM-killed-mid-debate signature.
    degraded, reason, msg, rem = degradation.classify_degradation(
        status="running", error_text=None, num_actions=0, runner_alive=False)
    assert degraded is True
    assert reason == degradation.SIMULATION_INCOMPLETE_RESOURCE
    # The remediation must mention Docker memory and the demonstrative-preset/full-run framing
    assert "Docker" in rem
    assert ("preset" in rem or "MIROSHARK_SIM_PLATFORM" in rem or
            "WONDERWALL_DEFAULT_MAX_ROUNDS" in rem or "16 GB" in rem)


def test_classify_failed_reasons_roundtrip():
    for reason in (degradation.GRAPH_UNSEEDED, degradation.NO_LLM_KEY,
                   degradation.SIMULATION_INCOMPLETE_RESOURCE):
        enc = degradation.encode_reason(reason, "boom")
        assert degradation.decode_reason(enc) == reason
        d, r, m, rem = degradation.classify_degradation(
            status="failed", error_text=enc, num_actions=0, runner_alive=False)
        assert d is True and r == reason and rem == degradation.REMEDIATION[reason]


def test_classify_prep_failure_buckets():
    assert degradation.classify_prep_failure(
        "No matching entities found, please check if the graph is built"
    ) == degradation.GRAPH_UNSEEDED
    assert degradation.classify_prep_failure(
        "OpenAI 401 Unauthorized: invalid api key"
    ) == degradation.NO_LLM_KEY
    assert degradation.classify_prep_failure(
        "process killed unexpectedly"
    ) == degradation.SIMULATION_INCOMPLETE_RESOURCE


def test_healthy_completed_with_actions_not_degraded():
    d, r, m, rem = degradation.classify_degradation(
        status="completed", error_text=None, num_actions=12, runner_alive=False)
    assert d is False and r is None


def test_running_with_live_runner_is_pending_not_degraded():
    d, r, m, rem = degradation.classify_degradation(
        status="running", error_text=None, num_actions=0, runner_alive=True)
    assert d is False  # genuinely in-flight, not an abort


def test_degraded_endpoint_returns_structured_200(client):
    # FAILED sim with an encoded no_llm_key reason -> structured 200, never 5xx.
    _FakeManager._state = _FakeState(
        SimulationStatus.FAILED,
        error=degradation.encode_reason(degradation.NO_LLM_KEY, "401 user not found"),
    )
    resp = client.get("/api/simulation/sim_x/consensus")
    assert resp.status_code == 200
    b = resp.get_json()
    assert b["success"] is True and b["degraded"] is True
    assert b["reason"] == degradation.NO_LLM_KEY
    assert b["simulation_consensus"] is None
    assert b["simulation_note"]["reason"] == degradation.NO_LLM_KEY
    assert b["simulation_note"]["remediation"]
