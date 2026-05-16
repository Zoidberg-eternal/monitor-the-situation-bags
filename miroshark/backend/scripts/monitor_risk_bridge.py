"""
Monitor Risk Bridge — feeds Hyperliquid risk scores and Bags.fm token data
from the Monitor the Situation risk engine into MiroShark simulations.

Fetches live market data from Monitor's API (default: http://localhost:8402)
and injects it as context into simulation agents each round, so their
trading decisions reflect real-world market conditions.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

try:
    import httpx
except ImportError:
    httpx = None


MONITOR_API_URL = os.environ.get("MONITOR_API_URL", "http://localhost:8402")
MONITOR_CACHE_TTL = int(os.environ.get("MONITOR_CACHE_TTL", "30"))


@dataclass
class RiskSnapshot:
    """Snapshot of Hyperliquid risk scores from Monitor."""
    timestamp: float = 0
    assets: List[Dict[str, Any]] = field(default_factory=list)
    portfolio_risk_score: float = 0
    alerts: List[str] = field(default_factory=list)

    def to_simulation_prompt(self) -> str:
        if not self.assets:
            return ""

        lines = ["# LIVE MARKET RISK DATA (Hyperliquid)"]
        lines.append(
            "Real-time risk scores from Hyperliquid perps. "
            "High-risk assets (score ≥60) may signal volatility — "
            "consider this when evaluating token narratives."
        )
        lines.append("")

        for a in self.assets:
            score = a.get("risk_score", 0)
            asset = a.get("asset", "?")
            mark = a.get("mark_price", 0)
            funding = a.get("funding_rate", 0)

            risk_label = "LOW"
            if score >= 60:
                risk_label = "HIGH"
            elif score >= 40:
                risk_label = "MODERATE"

            lines.append(f"  {asset}: risk={score:.0f} ({risk_label}) | "
                         f"price=${mark:,.2f} | funding={funding:.6f}")

            components = a.get("component_scores", {})
            if components:
                parts = []
                for k, v in components.items():
                    if v > 30:
                        parts.append(f"{k}={v:.0f}")
                if parts:
                    lines.append(f"    Elevated: {', '.join(parts)}")

        if self.alerts:
            lines.append("")
            lines.append("  ACTIVE ALERTS:")
            for alert in self.alerts[:5]:
                lines.append(f"    ⚠ {alert}")

        lines.append(f"\n  Portfolio risk: {self.portfolio_risk_score:.0f}/100")
        return "\n".join(lines)


@dataclass
class TokenSnapshot:
    """Snapshot of Bags.fm token launch data from Monitor."""
    timestamp: float = 0
    tokens: List[Dict[str, Any]] = field(default_factory=list)

    def to_simulation_prompt(self) -> str:
        if not self.tokens:
            return ""

        lines = ["# BAGS.FM TOKEN LAUNCH DATA (Live)"]
        lines.append(
            "Recent token launches with risk scores. Use this to "
            "inform your trading decisions."
        )
        lines.append("")

        for t in self.tokens[:10]:
            name = t.get("name", "?")
            symbol = t.get("symbol", "?")
            risk_score = t.get("risk_score", 0)
            volume_24h = t.get("volume_24h", 0)

            lines.append(f"  ${symbol} ({name}): risk={risk_score:.0f} | "
                         f"vol_24h=${volume_24h:,.0f}")

        return "\n".join(lines)


class MonitorRiskBridge:
    """Fetches live risk data from Monitor the Situation and provides
    formatted prompts for injection into simulation agents.

    Usage:
        bridge = MonitorRiskBridge()

        # Each round, before agent actions:
        risk_prompt = bridge.get_risk_prompt()
        token_prompt = bridge.get_token_prompt()
        inject_risk_context(agent, risk_prompt)
        inject_token_context(agent, token_prompt)
    """

    def __init__(self, api_url: str = MONITOR_API_URL, cache_ttl: int = MONITOR_CACHE_TTL):
        self.api_url = api_url.rstrip("/")
        self.cache_ttl = cache_ttl
        self.latest_risk: Optional[RiskSnapshot] = None
        self.latest_tokens: Optional[TokenSnapshot] = None
        self._client: Optional[httpx.Client] = None

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            if httpx is None:
                raise ImportError("httpx is required for MonitorRiskBridge")
            self._client = httpx.Client(timeout=10)
        return self._client

    def refresh_risk_scores(self):
        """Fetch current risk scores from Monitor API."""
        if (self.latest_risk and
                time.time() - self.latest_risk.timestamp < self.cache_ttl):
            return

        try:
            resp = self._get_client().get(f"{self.api_url}/api/v1/market/risk-scores")
            resp.raise_for_status()
            data = resp.json()

            self.latest_risk = RiskSnapshot(
                timestamp=time.time(),
                assets=data.get("assets", []),
                portfolio_risk_score=data.get("portfolio_risk_score", 0),
                alerts=data.get("alerts", []),
            )
        except Exception:
            pass

    def refresh_token_data(self):
        """Fetch current Bags.fm token launches from Monitor API."""
        if (self.latest_tokens and
                time.time() - self.latest_tokens.timestamp < self.cache_ttl):
            return

        try:
            resp = self._get_client().get(f"{self.api_url}/api/v1/tokens/launches")
            resp.raise_for_status()
            data = resp.json()

            self.latest_tokens = TokenSnapshot(
                timestamp=time.time(),
                tokens=data.get("tokens", []),
            )
        except Exception:
            pass

    def refresh_all(self):
        """Refresh both risk scores and token data."""
        self.refresh_risk_scores()
        self.refresh_token_data()

    def get_risk_prompt(self) -> str:
        self.refresh_risk_scores()
        if not self.latest_risk:
            return ""
        return self.latest_risk.to_simulation_prompt()

    def get_token_prompt(self) -> str:
        self.refresh_token_data()
        if not self.latest_tokens:
            return ""
        return self.latest_tokens.to_simulation_prompt()

    def get_combined_prompt(self) -> str:
        """Get both risk + token data in one prompt block."""
        self.refresh_all()
        parts = []
        if self.latest_risk:
            p = self.latest_risk.to_simulation_prompt()
            if p:
                parts.append(p)
        if self.latest_tokens:
            p = self.latest_tokens.to_simulation_prompt()
            if p:
                parts.append(p)
        return "\n\n".join(parts)

    def get_risk_data_for_simulation(self) -> Dict[str, Any]:
        """Return raw risk data dict for use in simulation config/events."""
        self.refresh_risk_scores()
        if not self.latest_risk:
            return {}
        return {
            "assets": self.latest_risk.assets,
            "portfolio_risk_score": self.latest_risk.portfolio_risk_score,
            "alerts": self.latest_risk.alerts,
        }

    def close(self):
        if self._client:
            self._client.close()
            self._client = None


# ── Injection helpers ──

_RISK_MARKER = "\n\n# LIVE MARKET RISK DATA"
_TOKEN_MARKER = "\n\n# BAGS.FM TOKEN LAUNCH DATA"


def inject_risk_context(agent, risk_text: str):
    """Inject Hyperliquid risk scores into an agent's system message."""
    if not risk_text:
        return
    content = agent.system_message.content
    marker_pos = content.find(_RISK_MARKER)
    if marker_pos != -1:
        next_marker = content.find("\n\n# ", marker_pos + len(_RISK_MARKER))
        if next_marker != -1:
            content = content[:marker_pos] + content[next_marker:]
        else:
            content = content[:marker_pos]
    agent.system_message.content = content + "\n\n" + risk_text


def inject_token_context(agent, token_text: str):
    """Inject Bags.fm token launch data into an agent's system message."""
    if not token_text:
        return
    content = agent.system_message.content
    marker_pos = content.find(_TOKEN_MARKER)
    if marker_pos != -1:
        next_marker = content.find("\n\n# ", marker_pos + len(_TOKEN_MARKER))
        if next_marker != -1:
            content = content[:marker_pos] + content[next_marker:]
        else:
            content = content[:marker_pos]
    agent.system_message.content = content + "\n\n" + token_text
