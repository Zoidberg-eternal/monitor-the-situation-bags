"""
Market Graph Bridge — extracts entities from Monitor the Situation market events
and adds them to MiroShark's Neo4j knowledge graph.

Converts risk alerts, token launches, and market signals into graph episodes
so simulation agents can be grounded in real market entity relationships.
"""

from __future__ import annotations

import os
import time
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

try:
    import httpx
except ImportError:
    httpx = None

from ..storage import GraphStorage

logger = logging.getLogger("miroshark.market_graph_bridge")

MONITOR_API_URL = os.environ.get("MONITOR_API_URL", "http://localhost:8402")


@dataclass
class MarketEntity:
    """An entity extracted from market data."""
    name: str
    entity_type: str
    attributes: Dict[str, Any] = field(default_factory=dict)


class MarketGraphBridge:
    """Bridges Monitor the Situation market data into MiroShark's knowledge graph.

    Fetches risk scores, alerts, and token data from Monitor's API, then
    converts them into text episodes that the NER extractor processes
    into graph entities and relationships.
    """

    def __init__(
        self,
        storage: GraphStorage,
        graph_id: str,
        api_url: str = MONITOR_API_URL,
    ):
        self.storage = storage
        self.graph_id = graph_id
        self.api_url = api_url.rstrip("/")
        self._client: Optional[httpx.Client] = None
        self._last_sync: float = 0
        self._sync_interval = 60

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            if httpx is None:
                raise ImportError("httpx is required for MarketGraphBridge")
            self._client = httpx.Client(timeout=15)
        return self._client

    def sync_market_data(self) -> int:
        """Fetch market data from Monitor and add as graph episodes.

        Returns the number of episodes added.
        """
        now = time.time()
        if now - self._last_sync < self._sync_interval:
            return 0

        self._last_sync = now
        episodes_added = 0

        try:
            episodes_added += self._sync_risk_scores()
        except Exception as e:
            logger.warning(f"Failed to sync risk scores: {e}")

        try:
            episodes_added += self._sync_token_launches()
        except Exception as e:
            logger.warning(f"Failed to sync token launches: {e}")

        try:
            episodes_added += self._sync_alerts()
        except Exception as e:
            logger.warning(f"Failed to sync alerts: {e}")

        if episodes_added > 0:
            logger.info(f"Synced {episodes_added} market episodes to graph {self.graph_id}")

        return episodes_added

    def _sync_risk_scores(self) -> int:
        resp = self._get_client().get(f"{self.api_url}/api/v1/market/risk-scores")
        resp.raise_for_status()
        data = resp.json()

        assets = data.get("assets", [])
        if not assets:
            return 0

        lines = []
        for asset in assets:
            name = asset.get("asset", "Unknown")
            score = asset.get("risk_score", 0)
            mark = asset.get("mark_price", 0)
            oracle = asset.get("oracle_price", 0)
            funding = asset.get("funding_rate", 0)
            components = asset.get("component_scores", {})

            line = (
                f"{name} is a cryptocurrency/commodity asset currently trading at "
                f"${mark:,.2f} (oracle: ${oracle:,.2f}). "
                f"Its composite risk score is {score:.0f}/100."
            )

            high_components = [
                f"{k} risk at {v:.0f}"
                for k, v in components.items()
                if v > 40
            ]
            if high_components:
                line += f" Elevated risk factors: {', '.join(high_components)}."

            if abs(funding) > 0.0001:
                direction = "positive" if funding > 0 else "negative"
                line += f" Funding rate is {direction} at {funding:.6f}."

            lines.append(line)

        portfolio_score = data.get("portfolio_risk_score", 0)
        lines.append(
            f"The overall market portfolio risk score is {portfolio_score:.0f}/100."
        )

        text = "\n".join(lines)
        self.storage.add_text(self.graph_id, text)
        return 1

    def _sync_token_launches(self) -> int:
        resp = self._get_client().get(f"{self.api_url}/api/v1/tokens/launches")
        resp.raise_for_status()
        data = resp.json()

        tokens = data.get("tokens", [])
        if not tokens:
            return 0

        lines = []
        for token in tokens[:15]:
            name = token.get("name", "Unknown")
            symbol = token.get("symbol", "?")
            risk = token.get("risk_score", 0)
            volume = token.get("volume_24h", 0)
            narrative = token.get("narrative", "")

            line = (
                f"${symbol} ({name}) is a token launched on Bags.fm "
                f"with a risk score of {risk:.0f}/100 and "
                f"24-hour volume of ${volume:,.0f}."
            )
            if narrative:
                line += f" Narrative: {narrative[:200]}"
            lines.append(line)

        text = "\n".join(lines)
        self.storage.add_text(self.graph_id, text)
        return 1

    def _sync_alerts(self) -> int:
        resp = self._get_client().get(f"{self.api_url}/api/v1/market/alerts")
        resp.raise_for_status()
        data = resp.json()

        alerts = data.get("alerts", [])
        if not alerts:
            return 0

        lines = [
            "MARKET ALERT: The following assets have triggered risk alerts "
            "(score ≥60), indicating elevated volatility or unusual market conditions:"
        ]
        for alert in alerts:
            if isinstance(alert, str):
                lines.append(f"- {alert}")
            elif isinstance(alert, dict):
                asset = alert.get("asset", "?")
                score = alert.get("risk_score", 0)
                reason = alert.get("alert", alert.get("reason", ""))
                lines.append(f"- {asset} (risk={score:.0f}): {reason}")

        text = "\n".join(lines)
        self.storage.add_text(self.graph_id, text)
        return 1

    def close(self):
        if self._client:
            self._client.close()
            self._client = None
