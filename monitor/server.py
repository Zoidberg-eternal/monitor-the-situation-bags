"""Hyperliquid market data API server.

The upstream risk engine that the Stellar x402 gateway proxies to.

Run:
    uvicorn monitor.server:app --host 0.0.0.0 --port 8402
    # or
    python -m monitor.server

Environment variables:
    HL_CACHE_TTL  — Hyperliquid data cache TTL in seconds (default: 60)
    HOST          — Listen host (default: 0.0.0.0)
    PORT          — Listen port (default: 8402)
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from decimal import Decimal

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware

from monitor.client import HyperliquidClient, DEFAULT_PERP_ASSETS
from monitor.risk import compute_asset_risk
from monitor.historical import fetch_candles, fetch_all_funding, analyze_candles, detect_events, analyze_funding
from monitor.bags_client import BagsClient
from monitor.token_risk import compute_token_risk
from monitor.swarm import generate_personas, run_debate, aggregate_consensus
from monitor.miroshark_client import MiroSharkClient

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Monitor the Situation — Risk Engine",
    description="Hyperliquid perps and Bags.fm token risk scores, alerts, and historical analysis.",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

# --- State ---

_hl_client: HyperliquidClient | None = None
_bags_client: BagsClient | None = None
_miroshark_client: MiroSharkClient | None = None
_volume_history: dict[str, list[float]] = {}
_previous_oi: dict[str, float] = {}
_HISTORY_WINDOW = 12

# Cache: mint -> {simulation_id, consensus, timestamp}
_simulation_cache: dict[str, dict] = {}
_SIM_CACHE_TTL = 300  # 5 minutes
_seen_mints: set[str] = set()
_AUTO_SIM_ENABLED = os.environ.get("AUTO_SIMULATE", "1").lower() in ("1", "true", "yes")
_AUTO_SIM_INTERVAL = int(os.environ.get("AUTO_SIMULATE_INTERVAL", "120"))

# --- Payment network ---
PAYMENT_NETWORK = os.environ.get("PAYMENT_NETWORK", "stellar")

# --- Pricing (for reference in responses) ---
PRICE_RISK_SCORES = Decimal("0.01")
PRICE_SINGLE_ASSET = Decimal("0.005")
PRICE_ALERTS = Decimal("0.005")
PRICE_PRICES = Decimal("0.002")
PRICE_HISTORICAL_BASE = Decimal("0.05")
PRICE_HISTORICAL_PER_DAY = Decimal("0.003")


PRICE_TOKEN_LAUNCHES = Decimal("0.005")
PRICE_TOKEN_RISK_SCORES = Decimal("0.01")
PRICE_TOKEN_SINGLE = Decimal("0.005")

PRICE_SWARM_CONSENSUS = Decimal("0.02")
PRICE_TOKEN_SENTIMENT = Decimal("0.02")
PRICE_DEEP_ANALYSIS = Decimal("0.05")


@app.on_event("startup")
async def startup():
    global _hl_client, _bags_client, _miroshark_client
    cache_ttl = int(os.environ.get("HL_CACHE_TTL", "60"))
    _hl_client = HyperliquidClient(cache_ttl=cache_ttl)
    _bags_client = BagsClient(cache_ttl=cache_ttl)
    _miroshark_client = MiroSharkClient()
    logger.info(
        "Risk engine started (cache_ttl=%ds, bags_api_key=%s, miroshark=%s)",
        cache_ttl,
        "set" if _bags_client.has_api_key else "not set",
        _miroshark_client._base_url,
    )
    if _AUTO_SIM_ENABLED:
        asyncio.create_task(_auto_simulate_loop())


async def _auto_simulate_loop():
    """Background task: detect new token launches and auto-trigger MiroShark simulations."""
    await asyncio.sleep(10)  # initial delay for services to settle
    while True:
        try:
            if _bags_client and _miroshark_client and _miroshark_client.is_available is not False:
                feed = _bags_client.fetch_launch_feed(limit=20)
                for token in feed:
                    mint = token.get("tokenMint", "")
                    if not mint or mint in _seen_mints:
                        continue
                    _seen_mints.add(mint)
                    scored = _score_token(token, _bags_client)
                    token_data = {
                        "name": scored["name"],
                        "ticker": scored["symbol"],
                        "description": f"Bags.fm token: {scored['name']} ({scored['symbol']})",
                        "team_info": f"Status: {scored['status']}",
                        "market_data": scored.get("pool_info", {}),
                        "market_context": {
                            "risk_score": scored["risk_score"],
                            "alerts": scored["alerts"],
                        },
                    }
                    sim_id = await _miroshark_client.trigger_simulation(token_data)
                    if sim_id:
                        _simulation_cache[mint] = {
                            "simulation_id": sim_id,
                            "consensus": None,
                            "timestamp": time.time(),
                        }
                        logger.info("Auto-triggered MiroShark simulation for %s (%s): %s", scored["symbol"], mint[:8], sim_id)
                # Poll for pending simulation results
                for mint, entry in list(_simulation_cache.items()):
                    if entry["consensus"] is not None:
                        continue
                    sim_id = entry.get("simulation_id")
                    if not sim_id:
                        continue
                    status = await _miroshark_client.get_status(sim_id)
                    if status and status.get("status") == "completed":
                        consensus = await _miroshark_client.get_consensus(sim_id)
                        if consensus:
                            entry["consensus"] = consensus
                            entry["timestamp"] = time.time()
                            logger.info("Cached MiroShark consensus for %s", mint[:8])
        except Exception:
            logger.exception("Auto-simulate loop error")
        await asyncio.sleep(_AUTO_SIM_INTERVAL)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "risk-engine"}


def _get_client() -> HyperliquidClient:
    if _hl_client is None:
        raise HTTPException(503, detail="Risk engine not initialized")
    return _hl_client


def _build_asset_snapshot(ctx: dict) -> dict:
    mark = float(ctx.get("mark_price") or 0)
    oracle = float(ctx.get("oracle_price") or 0)
    funding = float(ctx.get("funding_rate") or 0)
    oi = float(ctx.get("open_interest") or 0)
    volume = float(ctx.get("day_volume") or 0)
    asset = ctx["asset"]

    _volume_history.setdefault(asset, []).append(volume)
    if len(_volume_history[asset]) > _HISTORY_WINDOW:
        _volume_history[asset] = _volume_history[asset][-_HISTORY_WINDOW:]

    avg_vol = sum(_volume_history[asset]) / len(_volume_history[asset])
    prev_oi = _previous_oi.get(asset, oi)
    _previous_oi[asset] = oi

    return {
        "asset": asset,
        "mark_price": mark,
        "oracle_price": oracle,
        "funding_rate": funding,
        "open_interest": oi,
        "day_volume": volume,
        "avg_volume": round(avg_vol, 2),
        "previous_oi": prev_oi,
    }


def _score_asset(snapshot: dict) -> dict:
    risk = compute_asset_risk(
        asset=snapshot["asset"],
        funding_rate=snapshot["funding_rate"],
        current_volume=snapshot["day_volume"],
        avg_volume=snapshot["avg_volume"],
        current_oi=snapshot["open_interest"],
        previous_oi=snapshot["previous_oi"],
        mark_price=snapshot["mark_price"],
        oracle_price=snapshot["oracle_price"],
    )
    return {
        "asset": risk.asset,
        "mark_price": snapshot["mark_price"],
        "oracle_price": snapshot["oracle_price"],
        "funding_rate": snapshot["funding_rate"],
        "open_interest": snapshot["open_interest"],
        "day_volume": snapshot["day_volume"],
        "avg_volume": snapshot["avg_volume"],
        "risk_score": round(risk.composite, 1),
        "component_scores": {
            "funding": round(risk.funding_score, 1),
            "volume_spike": round(risk.volume_score, 1),
            "oi_shift": round(risk.oi_score, 1),
            "basis": round(risk.basis_score, 1),
        },
        "alerts": risk.alerts,
    }


# --- Endpoints ---

@app.get("/api/v1/market/risk-scores")
async def get_risk_scores(request: Request, assets: str | None = None):
    """All assets with composite risk scores."""
    client = _get_client()
    asset_list = [a.strip() for a in assets.split(",")] if assets else DEFAULT_PERP_ASSETS
    contexts = client.fetch_asset_contexts(asset_list)
    scored = [_score_asset(_build_asset_snapshot(ctx)) for ctx in contexts]

    portfolio_risk = (
        sum(s["risk_score"] for s in scored) / len(scored) if scored else 0.0
    )
    all_alerts = [a for s in scored for a in s["alerts"]]

    return {
        "timestamp": time.time(),
        "assets": scored,
        "portfolio_risk_score": round(portfolio_risk, 1),
        "alerts": all_alerts,
        "pricing": {"amount_usdc": str(PRICE_RISK_SCORES), "network": PAYMENT_NETWORK},
    }


@app.get("/api/v1/market/risk-scores/{asset}")
async def get_asset_risk(request: Request, asset: str):
    """Deep dive risk score for a single asset."""
    client = _get_client()
    contexts = client.fetch_asset_contexts([asset.upper()])
    if not contexts:
        raise HTTPException(404, detail=f"Asset '{asset}' not found")

    snapshot = _build_asset_snapshot(contexts[0])
    scored = _score_asset(snapshot)
    funding_history = client.fetch_funding_history(asset.upper())
    scored["funding_history_24h"] = funding_history[-24:] if funding_history else []
    book = client.fetch_orderbook_snapshot(asset.upper(), depth=5)
    scored["orderbook"] = book

    return {
        "timestamp": time.time(),
        **scored,
        "pricing": {"amount_usdc": str(PRICE_SINGLE_ASSET), "network": PAYMENT_NETWORK},
    }


@app.get("/api/v1/market/alerts")
async def get_alerts(request: Request, threshold: float = 60.0):
    """Active alerts only — assets with risk score >= threshold."""
    client = _get_client()
    contexts = client.fetch_asset_contexts(DEFAULT_PERP_ASSETS)
    scored = [_score_asset(_build_asset_snapshot(ctx)) for ctx in contexts]
    alerting = [s for s in scored if s["risk_score"] >= threshold]

    return {
        "timestamp": time.time(),
        "threshold": threshold,
        "alerting_assets": alerting,
        "total_monitored": len(scored),
        "pricing": {"amount_usdc": str(PRICE_ALERTS), "network": PAYMENT_NETWORK},
    }


@app.get("/api/v1/market/prices")
async def get_prices(request: Request, assets: str | None = None):
    """Raw price snapshot — no risk scoring."""
    client = _get_client()
    asset_list = [a.strip() for a in assets.split(",")] if assets else DEFAULT_PERP_ASSETS
    contexts = client.fetch_asset_contexts(asset_list)
    prices = []
    for ctx in contexts:
        prices.append({
            "asset": ctx["asset"],
            "mark_price": float(ctx.get("mark_price") or 0),
            "oracle_price": float(ctx.get("oracle_price") or 0),
            "funding_rate": float(ctx.get("funding_rate") or 0),
            "open_interest": float(ctx.get("open_interest") or 0),
            "day_volume": float(ctx.get("day_volume") or 0),
        })

    return {
        "timestamp": time.time(),
        "assets": prices,
        "pricing": {"amount_usdc": str(PRICE_PRICES), "network": PAYMENT_NETWORK},
    }


@app.get("/api/v1/market/historical")
async def get_historical(
    request: Request,
    assets: str | None = None,
    days: int = 30,
):
    """Historical analysis with candle data, funding stats, and notable events."""
    days = max(1, min(60, days))
    price = PRICE_HISTORICAL_BASE + PRICE_HISTORICAL_PER_DAY * days
    client = _get_client()
    asset_list = [a.strip() for a in assets.split(",")] if assets else DEFAULT_PERP_ASSETS

    now_ms = int(time.time() * 1000)
    start_ms = now_ms - (days * 86_400_000)

    asset_data = {}
    for asset_name in asset_list:
        candles = fetch_candles(client._info, asset_name, "1d", start_ms, now_ms)
        candle_days = analyze_candles(candles)
        candle_events = detect_events(candle_days, asset_name) if candle_days else []
        funding = fetch_all_funding(client._info, asset_name, start_ms, now_ms)
        funding_stats = analyze_funding(funding, asset_name)

        asset_data[asset_name] = {
            "candle_days": candle_days,
            "candle_events": candle_events,
            "funding_stats": funding_stats,
        }

    return {
        "timestamp": time.time(),
        "lookback_days": days,
        "assets": list(asset_data.keys()),
        "asset_data": asset_data,
        "pricing": {"amount_usdc": str(price), "network": PAYMENT_NETWORK},
    }


def _get_bags_client() -> BagsClient:
    if _bags_client is None:
        raise HTTPException(503, detail="Bags.fm client not initialized")
    return _bags_client


def _score_token(token: dict, bags: BagsClient) -> dict:
    mint = token["tokenMint"]
    symbol = token.get("symbol", "???")

    lifetime_fees_raw = bags.fetch_lifetime_fees(mint) if bags.has_api_key else None
    lifetime_fees = float(lifetime_fees_raw) if lifetime_fees_raw is not None else 0.0

    pool_info = bags.fetch_pool_info(mint) if bags.has_api_key else None
    pool_liquidity = 0.0
    if pool_info and isinstance(pool_info, dict):
        pool_liquidity = float(pool_info.get("liquidity", pool_info.get("tvl", 0)) or 0)

    risk = compute_token_risk(
        token_mint=mint,
        symbol=symbol,
        lifetime_fees_lamports=lifetime_fees,
        pool_liquidity=pool_liquidity,
    )

    result: dict = {
        "token_mint": mint,
        "name": token.get("name", ""),
        "symbol": symbol,
        "status": token.get("status", ""),
        "image": token.get("image", ""),
        "risk_score": round(risk.composite, 1),
        "component_scores": {
            "launch_velocity": round(risk.launch_velocity_score, 1),
            "fee_accumulation": round(risk.fee_score, 1),
            "liquidity_depth": round(risk.liquidity_score, 1),
            "volatility": round(risk.volatility_score, 1),
        },
        "alerts": risk.alerts,
    }
    if lifetime_fees_raw is not None:
        result["lifetime_fees_lamports"] = lifetime_fees
    if pool_info is not None:
        result["pool_info"] = pool_info
    return result


@app.get("/api/v1/tokens/launches")
async def get_token_launches(request: Request, limit: int = 50):
    """Recent Bags.fm token launches with risk scores."""
    bags = _get_bags_client()
    limit = max(1, min(100, limit))
    feed = bags.fetch_launch_feed(limit=limit)

    scored = [_score_token(t, bags) for t in feed]
    all_alerts = [a for s in scored for a in s["alerts"]]

    return {
        "timestamp": time.time(),
        "tokens": scored,
        "total": len(scored),
        "alerts": all_alerts,
        "bags_api_key_configured": bags.has_api_key,
        "pricing": {"amount_usdc": str(PRICE_TOKEN_LAUNCHES), "network": PAYMENT_NETWORK},
    }


@app.get("/api/v1/tokens/risk-scores")
async def get_token_risk_scores(
    request: Request,
    limit: int = 50,
    simulation_enriched: bool = False,
):
    """Risk scores for monitored Bags.fm tokens."""
    bags = _get_bags_client()
    limit = max(1, min(100, limit))
    feed = bags.fetch_launch_feed(limit=limit)

    scored = [_score_token(t, bags) for t in feed]
    scored.sort(key=lambda s: s["risk_score"], reverse=True)
    all_alerts = [a for s in scored for a in s["alerts"]]

    if simulation_enriched:
        for token_score in scored:
            mint = token_score.get("token_mint", "")
            cached = _simulation_cache.get(mint)
            if cached and cached.get("consensus") and (time.time() - cached["timestamp"]) < _SIM_CACHE_TTL:
                token_score["simulation"] = {
                    "simulation_id": cached.get("simulation_id"),
                    "predicted_direction": cached["consensus"].get("predicted_direction", "unknown"),
                    "confidence": cached["consensus"].get("confidence", 0),
                    "sentiment_distribution": cached["consensus"].get("sentiment_distribution", {}),
                }

    avg_risk = sum(s["risk_score"] for s in scored) / len(scored) if scored else 0.0

    return {
        "timestamp": time.time(),
        "tokens": scored,
        "average_risk_score": round(avg_risk, 1),
        "alerts": all_alerts,
        "simulation_enriched": simulation_enriched,
        "bags_api_key_configured": bags.has_api_key,
        "pricing": {"amount_usdc": str(PRICE_TOKEN_RISK_SCORES), "network": PAYMENT_NETWORK},
    }


@app.get("/api/v1/tokens/risk-scores/{mint}")
async def get_single_token_risk(request: Request, mint: str):
    """Risk score for a single Bags.fm token by mint address."""
    bags = _get_bags_client()

    feed = bags.fetch_launch_feed(limit=100)
    token = next((t for t in feed if t["tokenMint"] == mint), None)
    if token is None:
        raise HTTPException(404, detail=f"Token '{mint}' not found in recent launches")

    scored = _score_token(token, bags)

    creators = bags.fetch_creators(mint) if bags.has_api_key else None
    if creators is not None:
        scored["creators"] = creators

    return {
        "timestamp": time.time(),
        **scored,
        "bags_api_key_configured": bags.has_api_key,
        "pricing": {"amount_usdc": str(PRICE_TOKEN_SINGLE), "network": PAYMENT_NETWORK},
    }


@app.get("/api/v1/market/consensus")
async def get_market_consensus(
    request: Request,
    asset: str = "BTC",
    agents: int | None = None,
):
    """Swarm consensus risk assessment for a Hyperliquid asset."""
    client = _get_client()
    asset_upper = asset.upper()
    contexts = client.fetch_asset_contexts([asset_upper])
    if not contexts:
        raise HTTPException(404, detail=f"Asset '{asset}' not found")

    snapshot = _build_asset_snapshot(contexts[0])
    scored = _score_asset(snapshot)

    market_data = {
        "asset": asset_upper,
        "mark_price": snapshot["mark_price"],
        "oracle_price": snapshot["oracle_price"],
        "funding_rate": snapshot["funding_rate"],
        "open_interest": snapshot["open_interest"],
        "day_volume": snapshot["day_volume"],
        "avg_volume": snapshot["avg_volume"],
        "risk_score": scored["risk_score"],
        "component_scores": scored["component_scores"],
        "alerts": scored["alerts"],
    }

    personas = generate_personas(agents)
    assessments = await run_debate(personas, asset_upper, market_data)
    consensus = aggregate_consensus(assessments, personas)

    return {
        "timestamp": time.time(),
        "asset": asset_upper,
        "market_data": market_data,
        "swarm": {
            "num_agents": len(personas),
            "consensus_direction": consensus.direction,
            "direction_score": consensus.direction_score,
            "confidence": consensus.confidence,
            "risk_level": consensus.risk_level,
            "risk_score": consensus.risk_score,
            "dissent_ratio": consensus.dissent_ratio,
            "key_arguments": consensus.key_arguments,
            "agent_opinions": consensus.agent_opinions,
        },
        "pricing": {"amount_usdc": str(PRICE_SWARM_CONSENSUS), "network": PAYMENT_NETWORK},
    }


@app.get("/api/v1/tokens/sentiment")
async def get_token_sentiment(
    request: Request,
    mint: str | None = None,
    symbol: str | None = None,
    agents: int | None = None,
):
    """Swarm consensus sentiment for a Bags.fm token."""
    bags = _get_bags_client()
    feed = bags.fetch_launch_feed(limit=100)

    token = None
    if mint:
        token = next((t for t in feed if t["tokenMint"] == mint), None)
    elif symbol:
        token = next((t for t in feed if t.get("symbol", "").upper() == symbol.upper()), None)

    if token is None:
        detail = f"mint={mint}" if mint else f"symbol={symbol}" if symbol else "no mint or symbol provided"
        raise HTTPException(404, detail=f"Token not found: {detail}")

    scored = _score_token(token, bags)

    market_data = {
        "token_mint": scored["token_mint"],
        "name": scored["name"],
        "symbol": scored["symbol"],
        "status": scored["status"],
        "risk_score": scored["risk_score"],
        "component_scores": scored["component_scores"],
        "alerts": scored["alerts"],
    }
    if "pool_info" in scored:
        market_data["pool_info"] = scored["pool_info"]
    if "lifetime_fees_lamports" in scored:
        market_data["lifetime_fees_lamports"] = scored["lifetime_fees_lamports"]

    personas = generate_personas(agents)
    assessments = await run_debate(personas, scored["symbol"], market_data)
    consensus = aggregate_consensus(assessments, personas)

    return {
        "timestamp": time.time(),
        "token": scored,
        "swarm": {
            "num_agents": len(personas),
            "consensus_direction": consensus.direction,
            "direction_score": consensus.direction_score,
            "confidence": consensus.confidence,
            "risk_level": consensus.risk_level,
            "risk_score": consensus.risk_score,
            "dissent_ratio": consensus.dissent_ratio,
            "key_arguments": consensus.key_arguments,
            "agent_opinions": consensus.agent_opinions,
        },
        "pricing": {"amount_usdc": str(PRICE_TOKEN_SENTIMENT), "network": PAYMENT_NETWORK},
    }


@app.get("/api/v1/tokens/deep-analysis/{mint}")
async def get_deep_analysis(request: Request, mint: str):
    """Combined live risk score + MiroShark simulation consensus for a token."""
    bags = _get_bags_client()
    miroshark = _get_miroshark_client()

    feed = bags.fetch_launch_feed(limit=100)
    token = next((t for t in feed if t["tokenMint"] == mint), None)
    if token is None:
        raise HTTPException(404, detail=f"Token '{mint}' not found in recent launches")

    scored = _score_token(token, bags)

    creators = bags.fetch_creators(mint) if bags.has_api_key else None
    if creators is not None:
        scored["creators"] = creators

    # Check simulation cache
    cached = _simulation_cache.get(mint)
    simulation = None
    if cached and (time.time() - cached["timestamp"]) < _SIM_CACHE_TTL:
        simulation = cached["consensus"]
    else:
        # Try to trigger a new simulation and get results
        token_data = {
            "name": scored["name"],
            "ticker": scored["symbol"],
            "description": f"Bags.fm token: {scored['name']} ({scored['symbol']})",
            "team_info": f"Status: {scored['status']}",
            "market_data": scored.get("pool_info", {}),
            "market_context": {
                "risk_score": scored["risk_score"],
                "alerts": scored["alerts"],
            },
        }
        sim_id = await miroshark.trigger_simulation(token_data)
        if sim_id:
            # Poll briefly for results (simulation may complete quickly for cached configs)
            import asyncio
            for _ in range(3):
                await asyncio.sleep(2)
                status = await miroshark.get_status(sim_id)
                if status and status.get("status") == "completed":
                    consensus = await miroshark.get_consensus(sim_id)
                    if consensus:
                        simulation = consensus
                        _simulation_cache[mint] = {
                            "simulation_id": sim_id,
                            "consensus": consensus,
                            "timestamp": time.time(),
                        }
                    break

    # Posture B (ZERA-600): if no consensus yet, surface a clear, structured,
    # non-fatal explanation instead of an unexplained null. Still HTTP 200.
    simulation_note = None
    if simulation is None and sim_id:
        degraded = await miroshark.get_consensus(sim_id)
        if degraded and degraded.get("degraded"):
            simulation_note = {
                "state": "degraded",
                "reason": degraded.get("degraded_reason"),
                "remediation": degraded.get("remediation"),
            }
        else:
            simulation_note = {
                "state": "pending",
                "reason": "Simulation is still preparing/running; consensus not "
                          "ready within the request window. Poll "
                          "/api/v1/tokens/simulate/{id}/consensus.",
                "simulation_id": sim_id,
            }

    response = {
        "timestamp": time.time(),
        "token": scored,
        "risk_score": scored["risk_score"],
        "simulation_consensus": simulation,
        "simulation_available": simulation is not None,
        "simulation_note": simulation_note,
        "pricing": {"amount_usdc": str(PRICE_DEEP_ANALYSIS), "network": PAYMENT_NETWORK},
    }

    if simulation:
        response["agent_sentiment_distribution"] = simulation.get("sentiment_distribution", {})
        response["top_arguments"] = simulation.get("top_arguments", {})
        response["belief_trajectory"] = simulation.get("belief_trajectory", [])
        response["predicted_direction"] = simulation.get("predicted_direction", "unknown")

        # KYA (Know Your Agent) — pass MiroShark's cryptographic attestations
        # straight through. Signatures are re-verifiable against
        # MiroShark's /api/verify endpoint or by decoding the DIDs directly.
        response["agent_attestations"] = simulation.get("agent_attestations", [])
        response["sim_root_did"] = simulation.get("sim_root_did")
        response["manifest"] = simulation.get("manifest")
        response["manifest_signature"] = simulation.get("manifest_signature")

    return response


PRICE_MIROSHARK_SIM = Decimal("0.03")


def _get_miroshark_client() -> MiroSharkClient:
    if _miroshark_client is None:
        raise HTTPException(503, detail="MiroShark client not initialized")
    return _miroshark_client


@app.post("/api/v1/tokens/simulate")
async def trigger_miroshark_simulation(
    request: Request,
    mint: str | None = None,
    symbol: str | None = None,
):
    """Trigger a MiroShark social simulation for a Bags.fm token."""
    bags = _get_bags_client()
    miroshark = _get_miroshark_client()

    feed = bags.fetch_launch_feed(limit=100)
    token = None
    if mint:
        token = next((t for t in feed if t["tokenMint"] == mint), None)
    elif symbol:
        token = next((t for t in feed if t.get("symbol", "").upper() == symbol.upper()), None)

    if token is None:
        detail = f"mint={mint}" if mint else f"symbol={symbol}" if symbol else "no mint or symbol provided"
        raise HTTPException(404, detail=f"Token not found: {detail}")

    scored = _score_token(token, bags)

    token_data = {
        "name": scored["name"],
        "ticker": scored["symbol"],
        "description": f"Bags.fm token: {scored['name']} ({scored['symbol']})",
        "team_info": f"Status: {scored['status']}",
        "market_data": scored.get("pool_info", {}),
        "market_context": {
            "risk_score": scored["risk_score"],
            "alerts": scored["alerts"],
        },
    }

    sim_id = await miroshark.trigger_simulation(token_data)
    if sim_id is None:
        raise HTTPException(503, detail="MiroShark unavailable or simulation failed to start")

    return {
        "timestamp": time.time(),
        "simulation_id": sim_id,
        "status": "starting",
        "token": {"name": scored["name"], "symbol": scored["symbol"], "mint": scored["token_mint"]},
        "pricing": {"amount_usdc": str(PRICE_MIROSHARK_SIM), "network": PAYMENT_NETWORK},
    }


@app.get("/api/v1/tokens/simulate/{simulation_id}/consensus")
async def get_miroshark_consensus(request: Request, simulation_id: str):
    """Get MiroShark consensus results for a simulation."""
    miroshark = _get_miroshark_client()
    consensus = await miroshark.get_consensus(simulation_id)
    if consensus is None:
        raise HTTPException(503, detail="MiroShark unavailable or simulation not found")

    return {
        "timestamp": time.time(),
        **consensus,
        "pricing": {"amount_usdc": str(PRICE_MIROSHARK_SIM), "network": PAYMENT_NETWORK},
    }


@app.get("/api/v1/tokens/simulate/{simulation_id}/status")
async def get_miroshark_status(request: Request, simulation_id: str):
    """Get MiroShark simulation status."""
    miroshark = _get_miroshark_client()
    status = await miroshark.get_status(simulation_id)
    if status is None:
        raise HTTPException(503, detail="MiroShark unavailable or simulation not found")

    return {
        "timestamp": time.time(),
        "simulation_id": simulation_id,
        **status,
    }


if __name__ == "__main__":
    import uvicorn

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8402"))
    uvicorn.run("monitor.server:app", host=host, port=port, reload=False)
