"""
Unified Monitor × MiroShark API

Proxies risk data from Monitor the Situation and combines it with
MiroShark simulation data in a single API surface.

Endpoints:
    GET  /api/monitor/risk-scores           — Hyperliquid risk scores (proxied)
    GET  /api/monitor/risk-scores/<asset>    — Single asset risk (proxied)
    GET  /api/monitor/alerts                 — Active risk alerts (proxied)
    GET  /api/monitor/tokens/launches        — Bags.fm token launches (proxied)
    GET  /api/monitor/tokens/risk-scores     — Token risk scores (proxied)
    GET  /api/monitor/consensus              — Swarm consensus (proxied)
    POST /api/monitor/graph-sync             — Sync market data into knowledge graph
    GET  /api/monitor/status                 — Bridge health / connectivity check
"""

import os

from flask import Blueprint, jsonify, request

try:
    import httpx
except ImportError:
    httpx = None

monitor_bp = Blueprint("monitor", __name__)

MONITOR_API_URL = os.environ.get("MONITOR_API_URL", "http://localhost:8402")

_client = None


def _get_client():
    global _client
    if _client is None:
        if httpx is None:
            raise RuntimeError("httpx is required for Monitor proxy")
        _client = httpx.Client(timeout=15, base_url=MONITOR_API_URL)
    return _client


def _proxy_get(path: str):
    """Proxy a GET request to Monitor and return the JSON response."""
    try:
        params = dict(request.args)
        resp = _get_client().get(path, params=params)
        resp.raise_for_status()
        return jsonify(resp.json()), resp.status_code
    except httpx.ConnectError:
        return jsonify({
            "error": "Monitor risk engine not reachable",
            "monitor_url": MONITOR_API_URL,
        }), 502
    except httpx.HTTPStatusError as e:
        return jsonify({
            "error": f"Monitor returned {e.response.status_code}",
            "detail": e.response.text[:500],
        }), e.response.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@monitor_bp.route("/status", methods=["GET"])
def monitor_status():
    """Check connectivity to Monitor the Situation risk engine."""
    try:
        resp = _get_client().get("/health")
        resp.raise_for_status()
        monitor_health = resp.json()
    except Exception as e:
        monitor_health = {"status": "unreachable", "error": str(e)}

    return jsonify({
        "bridge": "ok",
        "monitor_url": MONITOR_API_URL,
        "monitor_health": monitor_health,
    })


@monitor_bp.route("/risk-scores", methods=["GET"])
def risk_scores():
    return _proxy_get("/api/v1/market/risk-scores")


@monitor_bp.route("/risk-scores/<asset>", methods=["GET"])
def risk_scores_asset(asset: str):
    return _proxy_get(f"/api/v1/market/risk-scores/{asset}")


@monitor_bp.route("/alerts", methods=["GET"])
def alerts():
    return _proxy_get("/api/v1/market/alerts")


@monitor_bp.route("/prices", methods=["GET"])
def prices():
    return _proxy_get("/api/v1/market/prices")


@monitor_bp.route("/historical", methods=["GET"])
def historical():
    return _proxy_get("/api/v1/market/historical")


@monitor_bp.route("/consensus", methods=["GET"])
def consensus():
    return _proxy_get("/api/v1/market/consensus")


@monitor_bp.route("/tokens/launches", methods=["GET"])
def token_launches():
    return _proxy_get("/api/v1/tokens/launches")


@monitor_bp.route("/tokens/risk-scores", methods=["GET"])
def token_risk_scores():
    return _proxy_get("/api/v1/tokens/risk-scores")


@monitor_bp.route("/tokens/risk-scores/<mint>", methods=["GET"])
def token_risk_single(mint: str):
    return _proxy_get(f"/api/v1/tokens/risk-scores/{mint}")


@monitor_bp.route("/tokens/sentiment", methods=["GET"])
def token_sentiment():
    return _proxy_get("/api/v1/tokens/sentiment")


@monitor_bp.route("/graph-sync", methods=["POST"])
def graph_sync():
    """Manually trigger a sync of market data into a knowledge graph.

    Request JSON:
        { "graph_id": "...", "project_id": "..." }
    """
    data = request.get_json() or {}
    graph_id = data.get("graph_id")

    if not graph_id:
        return jsonify({"error": "graph_id is required"}), 400

    try:
        from flask import current_app
        from ..services.market_graph_bridge import MarketGraphBridge

        storage = current_app.extensions.get("neo4j_storage")
        if not storage:
            return jsonify({"error": "Neo4j storage not initialized"}), 503
        bridge = MarketGraphBridge(
            storage=storage,
            graph_id=graph_id,
            api_url=MONITOR_API_URL,
        )
        bridge._sync_interval = 0
        episodes = bridge.sync_market_data()
        bridge.close()

        return jsonify({
            "success": True,
            "episodes_added": episodes,
            "graph_id": graph_id,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
