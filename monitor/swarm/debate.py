"""Debate simulation — each agent persona assesses market data via LLM."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass

from monitor.swarm.personas import AgentPersona

logger = logging.getLogger(__name__)

SWARM_MODEL = os.environ.get("SWARM_MODEL", "claude-sonnet-4-20250514")

ASSESSMENT_PROMPT = """\
You are evaluating market data for {asset_label}. Respond with ONLY a JSON object, no other text.

## Market Data
{market_data}

## Instructions
Based on the data above and your analytical perspective, produce a risk assessment.

Respond with this exact JSON structure:
{{
  "direction": "bullish" | "bearish" | "neutral",
  "confidence": <float 0.0 to 1.0>,
  "risk_level": "low" | "medium" | "high" | "extreme",
  "reasoning": "<2-3 sentence explanation>"
}}
"""


@dataclass
class AgentAssessment:
    agent_name: str
    archetype: str
    direction: str  # bullish, bearish, neutral
    confidence: float  # 0.0 to 1.0
    risk_level: str  # low, medium, high, extreme
    reasoning: str


def _format_market_data(data: dict) -> str:
    lines = []
    for key, value in data.items():
        if isinstance(value, float):
            lines.append(f"- {key}: {value:.6f}")
        elif isinstance(value, dict):
            lines.append(f"- {key}:")
            for k, v in value.items():
                lines.append(f"  - {k}: {v}")
        else:
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


async def _assess_single(
    persona: AgentPersona,
    asset_label: str,
    market_data: dict,
    api_key: str | None = None,
) -> AgentAssessment:
    """Run a single agent's assessment via the Anthropic API."""
    import anthropic

    client = anthropic.AsyncAnthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))

    formatted = _format_market_data(market_data)
    user_msg = ASSESSMENT_PROMPT.format(
        asset_label=asset_label,
        market_data=formatted,
    )

    try:
        response = await client.messages.create(
            model=SWARM_MODEL,
            max_tokens=300,
            system=persona.system_prompt,
            messages=[{"role": "user", "content": user_msg}],
        )
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        parsed = json.loads(raw)

        return AgentAssessment(
            agent_name=persona.name,
            archetype=persona.archetype,
            direction=parsed.get("direction", "neutral"),
            confidence=max(0.0, min(1.0, float(parsed.get("confidence", 0.5)))),
            risk_level=parsed.get("risk_level", "medium"),
            reasoning=parsed.get("reasoning", "No reasoning provided."),
        )
    except Exception as e:
        logger.warning("Agent %s failed assessment: %s", persona.name, e)
        return AgentAssessment(
            agent_name=persona.name,
            archetype=persona.archetype,
            direction="neutral",
            confidence=0.0,
            risk_level="medium",
            reasoning=f"Assessment failed: {e}",
        )


async def run_debate(
    personas: list[AgentPersona],
    asset_label: str,
    market_data: dict,
    api_key: str | None = None,
) -> list[AgentAssessment]:
    """Run all agent assessments concurrently and return their opinions."""
    tasks = [
        _assess_single(persona, asset_label, market_data, api_key)
        for persona in personas
    ]
    return await asyncio.gather(*tasks)
