"""Consensus aggregation — weighted ensemble of agent opinions."""

from __future__ import annotations

from dataclasses import dataclass, field

from monitor.swarm.personas import AgentPersona
from monitor.swarm.debate import AgentAssessment

DIRECTION_SCORES = {"bullish": 1.0, "neutral": 0.0, "bearish": -1.0}
RISK_SCORES = {"low": 0.0, "medium": 0.33, "high": 0.66, "extreme": 1.0}


@dataclass
class SwarmConsensus:
    direction: str  # bullish, bearish, neutral
    direction_score: float  # -1.0 to 1.0
    confidence: float  # 0.0 to 1.0
    risk_level: str
    risk_score: float  # 0.0 to 1.0
    dissent_ratio: float  # fraction of agents disagreeing with consensus
    key_arguments: list[str]
    agent_opinions: list[dict] = field(default_factory=list)


def _direction_label(score: float) -> str:
    if score > 0.2:
        return "bullish"
    if score < -0.2:
        return "bearish"
    return "neutral"


def _risk_label(score: float) -> str:
    if score >= 0.75:
        return "extreme"
    if score >= 0.50:
        return "high"
    if score >= 0.25:
        return "medium"
    return "low"


def aggregate_consensus(
    assessments: list[AgentAssessment],
    personas: list[AgentPersona],
) -> SwarmConsensus:
    """Produce weighted consensus from individual agent assessments."""
    if not assessments:
        return SwarmConsensus(
            direction="neutral",
            direction_score=0.0,
            confidence=0.0,
            risk_level="medium",
            risk_score=0.33,
            dissent_ratio=0.0,
            key_arguments=[],
        )

    persona_weights = {p.name: p.weight for p in personas}
    total_weight = 0.0
    weighted_direction = 0.0
    weighted_confidence = 0.0
    weighted_risk = 0.0

    for a in assessments:
        w = persona_weights.get(a.agent_name, 1.0) * max(a.confidence, 0.1)
        total_weight += w
        weighted_direction += DIRECTION_SCORES.get(a.direction, 0.0) * w
        weighted_confidence += a.confidence * w
        weighted_risk += RISK_SCORES.get(a.risk_level, 0.33) * w

    if total_weight <= 0:
        total_weight = 1.0

    direction_score = weighted_direction / total_weight
    avg_confidence = weighted_confidence / total_weight
    avg_risk = weighted_risk / total_weight

    consensus_dir = _direction_label(direction_score)
    dissenting = sum(1 for a in assessments if a.direction != consensus_dir)
    dissent_ratio = dissenting / len(assessments)

    key_arguments = []
    for a in assessments:
        tag = f"[{a.agent_name}/{a.archetype}]"
        key_arguments.append(f"{tag} {a.direction} (conf={a.confidence:.2f}): {a.reasoning}")

    agent_opinions = [
        {
            "agent": a.agent_name,
            "archetype": a.archetype,
            "direction": a.direction,
            "confidence": round(a.confidence, 3),
            "risk_level": a.risk_level,
            "reasoning": a.reasoning,
        }
        for a in assessments
    ]

    return SwarmConsensus(
        direction=consensus_dir,
        direction_score=round(direction_score, 4),
        confidence=round(avg_confidence, 4),
        risk_level=_risk_label(avg_risk),
        risk_score=round(avg_risk, 4),
        dissent_ratio=round(dissent_ratio, 4),
        key_arguments=key_arguments,
        agent_opinions=agent_opinions,
    )
