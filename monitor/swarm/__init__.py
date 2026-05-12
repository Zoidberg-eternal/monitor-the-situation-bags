"""Swarm intelligence layer — multi-agent consensus risk assessment."""

from monitor.swarm.personas import ARCHETYPES, AgentPersona, generate_personas
from monitor.swarm.debate import run_debate, AgentAssessment
from monitor.swarm.consensus import aggregate_consensus, SwarmConsensus

__all__ = [
    "ARCHETYPES",
    "AgentPersona",
    "generate_personas",
    "run_debate",
    "AgentAssessment",
    "aggregate_consensus",
    "SwarmConsensus",
]
