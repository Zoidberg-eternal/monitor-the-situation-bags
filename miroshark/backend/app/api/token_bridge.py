"""
Token Bridge API — endpoints for Monitor×MiroShark integration.
Allows triggering simulations from token metadata and retrieving consensus results.
"""

import json
import os
import threading
import traceback
import uuid
from datetime import datetime

from flask import Blueprint, jsonify, request

from ..config import Config
from ..seed import SEED_GRAPH_ID
from ..seed.seed_loader import seed_graph_has_entities
from ..services.simulation_manager import SimulationManager, SimulationStatus
from ..services.simulation_runner import SimulationRunner
from ..services.agent_credentials import (
    SimulationKeyring,
    content_hash as ac_content_hash,
    sign_payload as ac_sign_payload,
)
from ..utils.logger import get_logger

logger = get_logger('miroshark.api.token_bridge')

token_bridge_bp = Blueprint('token_bridge', __name__)


def _generate_document_from_token(token_data: dict) -> str:
    """Generate a synthetic document from token metadata for the simulation pipeline."""
    name = token_data.get("name", "Unknown Token")
    ticker = token_data.get("ticker", "???")
    description = token_data.get("description", "No description provided.")
    team_info = token_data.get("team_info", "No team information available.")
    market_data = token_data.get("market_data", {})
    market_context = token_data.get("market_context", {})

    price = market_data.get("price", "N/A")
    volume = market_data.get("volume_24h", "N/A")
    liquidity = market_data.get("liquidity", "N/A")
    market_cap = market_data.get("market_cap", "N/A")

    risk_score = market_context.get("risk_score", "N/A")
    alerts = market_context.get("alerts", [])
    alerts_text = ", ".join(alerts) if alerts else "None"

    return f"""# {name} (${ticker}) — Token Analysis Document

## Overview
{description}

## Team & Background
{team_info}

## Market Data (Current)
- Price: ${price}
- 24h Volume: ${volume}
- Liquidity: ${liquidity}
- Market Cap: {market_cap}

## Risk Assessment
- Risk Score: {risk_score}/100
- Active Alerts: {alerts_text}

## Discussion Points
Investors and analysts are debating whether ${ticker} represents a viable investment opportunity.
Key considerations include the team's track record, current liquidity levels, trading volume
patterns, and the overall risk profile of the token.

The community is divided on the outlook for ${ticker}. Some see the current price as an
entry opportunity given the project fundamentals, while others point to risk factors
such as {alerts_text.lower() if alerts_text != "None" else "limited track record"}.
"""


def _run_simulation_pipeline(simulation_id: str, token_data: dict, document_text: str):
    """Background thread: prepare and start the simulation."""
    try:
        manager = SimulationManager()
        storage = None
        try:
            from flask import current_app
            storage = current_app.config.get('NEO4J_STORAGE')
        except RuntimeError:
            pass

        if not storage:
            logger.error(f"[{simulation_id}] No Neo4j storage available")
            state = manager._load_simulation_state(simulation_id)
            if state:
                state.status = SimulationStatus.FAILED
                state.error = "Neo4j storage not available"
                manager._save_simulation_state(state)
            return

        ticker = token_data.get("ticker", "TOKEN")
        requirement = (
            f"Simulate a social media discussion about the cryptocurrency token "
            f"{token_data.get('name', ticker)} (${ticker}). Agents should debate "
            f"whether this token is a good investment based on the provided market data "
            f"and risk assessment. Include bullish, bearish, and neutral perspectives."
        )

        # --- Posture A wiring (ZERA-600) ---------------------------------
        # The token bridge mints a fresh per-simulation graph_id that nobody
        # ingests into, so on the documented one-command path that graph is
        # empty and prep fails. If the per-sim graph has no entities, fall
        # back to the static, synthetic seed persona cohort so prep can reach
        # READY with zero manual steps. Not an ingest — just persona sourcing.
        sim_state = manager._load_simulation_state(simulation_id)
        try:
            from ..services.entity_reader import EntityReader
            per_sim_entities = EntityReader(storage).get_all_nodes(sim_state.graph_id)
        except Exception:
            per_sim_entities = []
        if not per_sim_entities and seed_graph_has_entities(storage):
            logger.info(
                "[%s] per-sim graph %s empty — falling back to seed graph %s",
                simulation_id, sim_state.graph_id, SEED_GRAPH_ID,
            )
            sim_state.graph_id = SEED_GRAPH_ID
            manager._save_simulation_state(sim_state)

        manager.prepare_simulation(
            simulation_id=simulation_id,
            simulation_requirement=requirement,
            document_text=document_text,
            use_llm_for_profiles=True,
            storage=storage,
        )

        state = manager._load_simulation_state(simulation_id)
        if state and state.status == SimulationStatus.READY:
            SimulationRunner.start_simulation(
                simulation_id=simulation_id,
                platform='parallel',
            )
            logger.info(f"[{simulation_id}] Simulation started for token {ticker}")
        else:
            # --- Posture B (ZERA-600): never leave a silent/opaque failure.
            # Record a structured, actionable reason so /consensus can return
            # a clear degraded payload instead of an unexplained null.
            reason = (state.error if state and state.error else "preparation did not reach READY")
            if state:
                if state.status != SimulationStatus.FAILED:
                    state.status = SimulationStatus.FAILED
                if not state.error:
                    state.error = (
                        "Knowledge graph not populated. The static demo seed did "
                        "not load — recreate the stack with "
                        "`docker compose down -v && docker compose up --build` "
                        "so the empty-Neo4j seed step runs."
                    )
                manager._save_simulation_state(state)
            logger.warning(
                "[%s] Preparation did not reach READY state: %s (%s)",
                simulation_id, state.status if state else 'None', reason,
            )

    except Exception as e:
        logger.error(f"[{simulation_id}] Pipeline failed: {e}\n{traceback.format_exc()}")
        try:
            manager = SimulationManager()
            state = manager._load_simulation_state(simulation_id)
            if state:
                state.status = SimulationStatus.FAILED
                state.error = str(e)
                manager._save_simulation_state(state)
        except Exception:
            pass


@token_bridge_bp.route('/from-token', methods=['POST'])
def create_from_token():
    """
    Create and start a simulation from token metadata.

    Request (JSON):
        {
            "name": "TokenName",
            "ticker": "TKN",
            "description": "A token for X purpose",
            "team_info": "Founded by A, B",
            "market_data": {"price": 0.05, "volume_24h": 50000, "liquidity": 100000},
            "market_context": {"risk_score": 72, "alerts": ["high volume spike"]}
        }

    Returns:
        {"simulation_id": "sim_xxx", "status": "starting"}
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "JSON body required"}), 400

        if not data.get("name") and not data.get("ticker"):
            return jsonify({"success": False, "error": "name or ticker required"}), 400

        document_text = _generate_document_from_token(data)

        project_id = f"token_{data.get('ticker', 'UNK').lower()}_{uuid.uuid4().hex[:8]}"
        graph_id = f"miroshark_{uuid.uuid4().hex[:12]}"

        manager = SimulationManager()
        state = manager.create_simulation(
            project_id=project_id,
            graph_id=graph_id,
            enable_twitter=True,
            enable_reddit=True,
        )

        from flask import current_app
        app = current_app._get_current_object()

        def _run_in_app_context():
            with app.app_context():
                _run_simulation_pipeline(state.simulation_id, data, document_text)

        thread = threading.Thread(target=_run_in_app_context, daemon=True)
        thread.start()

        return jsonify({
            "success": True,
            "simulation_id": state.simulation_id,
            "status": "starting",
            "project_id": project_id,
        })

    except Exception as e:
        logger.error(f"from-token failed: {e}\n{traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


@token_bridge_bp.route('/<simulation_id>/consensus', methods=['GET'])
def get_consensus(simulation_id: str):
    """
    Get aggregated consensus from a completed (or in-progress) simulation.

    Returns:
        {
            "simulation_id": "sim_abc123",
            "status": "completed",
            "rounds_completed": 5,
            "sentiment_distribution": {"bullish": 0.45, "bearish": 0.30, "neutral": 0.25},
            "top_arguments": {
                "bullish": ["Strong team background", ...],
                "bearish": ["Low initial liquidity", ...]
            },
            "belief_trajectory": [{"round": 1, "bullish": 0.5}, ...],
            "predicted_direction": "cautiously_bullish",
            "confidence": 0.62
        }
    """
    try:
        manager = SimulationManager()
        state = manager.get_simulation(simulation_id)
        if not state:
            return jsonify({"success": False, "error": "Simulation not found"}), 404

        # --- Posture B (ZERA-600): graceful degradation -------------------
        # A prep failure (e.g. empty knowledge graph on the one-command path)
        # must surface as a clear, structured, non-fatal payload — HTTP 200,
        # success=true, consensus explicitly degraded — never a silent null
        # or an unexplained 5xx for the caller to guess at.
        status_str = state.status.value if hasattr(state.status, 'value') else str(state.status)
        if state.status == SimulationStatus.FAILED:
            note = state.error or (
                "Simulation preparation failed before any agent ran. The "
                "knowledge graph was not populated."
            )
            logger.warning(
                "[%s] consensus requested on FAILED sim — returning degraded payload",
                simulation_id,
            )
            return jsonify({
                "success": True,
                "simulation_id": simulation_id,
                "status": status_str,
                "degraded": True,
                "degraded_reason": note,
                "remediation": (
                    "Recreate the stack with "
                    "`docker compose down -v && docker compose up --build` so "
                    "the empty-Neo4j static seed step runs, then retry."
                ),
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
            }), 200

        actions = SimulationRunner.get_actions(simulation_id=simulation_id, limit=10000)

        # Load (or rehydrate from disk) the simulation's keyring so we can build
        # signed attestations + a root-signed manifest below.
        sim_dir = os.path.join(SimulationRunner.RUN_STATE_DIR, simulation_id)
        keyring = SimulationKeyring.lookup(simulation_id)
        if keyring is None and os.path.exists(os.path.join(sim_dir, "agent_keys.json")):
            keyring = SimulationKeyring.for_simulation(simulation_id, sim_dir)

        rounds_completed = 0
        round_sentiments = {}
        all_posts = []
        agent_contributions: dict = {}  # agent_id -> {name, posts: [(round, sentiment, content)]}

        for action in actions:
            ad = action.to_dict()
            r = ad.get("round_num", 0)
            if r > rounds_completed:
                rounds_completed = r

            if ad.get("action_type") in ("CREATE_POST", "REPOST", "COMMENT"):
                content = ""
                if isinstance(ad.get("result"), str):
                    content = ad["result"]
                elif isinstance(ad.get("action_args"), dict):
                    content = ad["action_args"].get("content", "")

                sentiment = _classify_sentiment(content)
                all_posts.append({"round": r, "sentiment": sentiment, "content": content, "agent": ad.get("agent_name", "")})

                if r not in round_sentiments:
                    round_sentiments[r] = {"bullish": 0, "bearish": 0, "neutral": 0}
                round_sentiments[r][sentiment] += 1

                aid = ad.get("agent_id")
                if aid is not None:
                    bucket = agent_contributions.setdefault(aid, {
                        "agent_id": aid,
                        "agent_name": ad.get("agent_name", ""),
                        "posts": [],
                    })
                    bucket["posts"].append({
                        "round": r,
                        "sentiment": sentiment,
                        "content": content,
                        "timestamp": ad.get("timestamp"),
                    })

        total_posts = len(all_posts)
        if total_posts > 0:
            bullish = sum(1 for p in all_posts if p["sentiment"] == "bullish")
            bearish = sum(1 for p in all_posts if p["sentiment"] == "bearish")
            neutral = total_posts - bullish - bearish
            sentiment_dist = {
                "bullish": round(bullish / total_posts, 3),
                "bearish": round(bearish / total_posts, 3),
                "neutral": round(neutral / total_posts, 3),
            }
        else:
            sentiment_dist = {"bullish": 0, "bearish": 0, "neutral": 0}

        belief_trajectory = []
        for r in sorted(round_sentiments.keys()):
            counts = round_sentiments[r]
            total = sum(counts.values()) or 1
            belief_trajectory.append({
                "round": r,
                "bullish": round(counts["bullish"] / total, 3),
                "bearish": round(counts["bearish"] / total, 3),
                "neutral": round(counts["neutral"] / total, 3),
            })

        top_bullish = [p["content"][:200] for p in all_posts if p["sentiment"] == "bullish"][:5]
        top_bearish = [p["content"][:200] for p in all_posts if p["sentiment"] == "bearish"][:5]

        bull_pct = sentiment_dist.get("bullish", 0)
        bear_pct = sentiment_dist.get("bearish", 0)
        if bull_pct > bear_pct + 0.15:
            direction = "bullish"
        elif bear_pct > bull_pct + 0.15:
            direction = "bearish"
        elif bull_pct > bear_pct:
            direction = "cautiously_bullish"
        elif bear_pct > bull_pct:
            direction = "cautiously_bearish"
        else:
            direction = "neutral"

        confidence = round(abs(bull_pct - bear_pct) + 0.3 * (1 - sentiment_dist.get("neutral", 0)), 3)
        confidence = min(confidence, 1.0)

        # ---- KYA: per-agent signed attestations + root-signed manifest -------
        agent_attestations = []
        if keyring is not None:
            for aid, bucket in agent_contributions.items():
                cred = keyring.get(aid)
                if not cred:
                    continue
                # Roll the agent's contributions into a per-agent stance.
                counts = {"bullish": 0, "bearish": 0, "neutral": 0}
                for p in bucket["posts"]:
                    counts[p["sentiment"]] += 1
                total = sum(counts.values()) or 1
                stance = max(counts, key=counts.get)
                agent_confidence = round(counts[stance] / total, 3)
                # Pick the most representative quote (first post matching the stance).
                quote = next(
                    (p["content"] for p in bucket["posts"] if p["sentiment"] == stance),
                    bucket["posts"][0]["content"] if bucket["posts"] else "",
                )
                signed_at = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
                attest_payload = {
                    "agent_did": cred.did,
                    "agent_name": bucket["agent_name"],
                    "sim_id": simulation_id,
                    "stance": stance,
                    "confidence": agent_confidence,
                    "post_count": total,
                    "quote_hash": ac_content_hash({"quote": quote}),
                    "signed_at": signed_at,
                }
                signature = ac_sign_payload(cred.private_bytes(), attest_payload)
                agent_attestations.append({
                    **attest_payload,
                    "signature": signature,
                })

        manifest = {
            "kind": "miroshark.consensus.manifest.v1",
            "simulation_id": simulation_id,
            "rounds_completed": rounds_completed,
            "total_posts_analyzed": total_posts,
            "sentiment_distribution": sentiment_dist,
            "predicted_direction": direction,
            "confidence": confidence,
            "attestation_count": len(agent_attestations),
            "attestations_hash": ac_content_hash([a["signature"] for a in agent_attestations]),
            "signed_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
        }
        manifest_signature = None
        sim_root_did = None
        if keyring is not None:
            root_cred = keyring.root_credential()
            sim_root_did = root_cred.did
            manifest_signature = ac_sign_payload(root_cred.private_bytes(), manifest)

        return jsonify({
            "success": True,
            "simulation_id": simulation_id,
            "status": state.status.value if hasattr(state.status, 'value') else str(state.status),
            "rounds_completed": rounds_completed,
            "total_posts_analyzed": total_posts,
            "sentiment_distribution": sentiment_dist,
            "top_arguments": {
                "bullish": top_bullish,
                "bearish": top_bearish,
            },
            "belief_trajectory": belief_trajectory,
            "predicted_direction": direction,
            "confidence": confidence,
            "agent_attestations": agent_attestations,
            "sim_root_did": sim_root_did,
            "manifest": manifest,
            "manifest_signature": manifest_signature,
        })

    except Exception as e:
        logger.error(f"consensus failed for {simulation_id}: {e}\n{traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


_BULLISH_KEYWORDS = {"buy", "bullish", "moon", "pump", "growth", "undervalued", "opportunity", "strong", "promising", "upside", "invest", "long"}
_BEARISH_KEYWORDS = {"sell", "bearish", "dump", "crash", "overvalued", "risk", "scam", "rug", "avoid", "short", "weak", "decline"}


def _classify_sentiment(text: str) -> str:
    """Simple keyword-based sentiment classification."""
    if not text:
        return "neutral"
    lower = text.lower()
    bull_score = sum(1 for w in _BULLISH_KEYWORDS if w in lower)
    bear_score = sum(1 for w in _BEARISH_KEYWORDS if w in lower)
    if bull_score > bear_score:
        return "bullish"
    elif bear_score > bull_score:
        return "bearish"
    return "neutral"
