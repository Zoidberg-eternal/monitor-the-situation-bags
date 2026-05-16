"""Idempotent static-seed loader for the Monitor x MiroShark demo (ZERA-600).

Posture A (bounded static seed): on backend startup we load a small,
version-controlled, fully synthetic persona knowledge graph **only when the
Neo4j database is completely empty** (`MATCH (n) RETURN count(n) == 0`). This
is not an ingest/crawler — the fixture lives in ``bags_demo_graph.json`` and is
written verbatim via parametrized Cypher.

Why this exists: the documented one-command judge path
(``docker compose down -v && docker compose up --build``) boots an empty
Neo4j. MiroShark's simulation *preparation* reads persona entities from the
graph and fails instantly with zero entities, so the token-bridge consensus is
permanently ``null``. Seeding a static persona cohort lets ``prepare_simulation``
reach ``READY`` on a fresh volume with no manual step.

Idempotency / safety contract:
  * Runs the write only when the whole DB has zero nodes.
  * All writes are ``MERGE`` on stable ``uuid`` keys, so even a racing/partial
    run cannot duplicate or clobber.
  * Re-running ``docker compose up`` on a populated volume is a no-op.
  * Never raises into startup — a seed failure logs and degrades to Posture B.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Optional

from ..utils.logger import get_logger

logger = get_logger("miroshark.seed")

# Stable, documented graph id the token-bridge falls back to when its
# per-simulation graph is empty. Versioned so a future fixture revision is an
# explicit new id rather than a silent mutation.
SEED_GRAPH_ID = "miroshark_bags_seed_v1"

_FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "bags_demo_graph.json")


def _load_fixture() -> dict:
    with open(_FIXTURE_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


def seed_graph_has_entities(storage) -> bool:
    """True if the static seed graph already holds at least one entity."""
    try:
        with storage._driver.session() as session:
            rec = session.run(
                "MATCH (n:Entity {graph_id: $gid}) RETURN count(n) AS c",
                gid=SEED_GRAPH_ID,
            ).single()
            return bool(rec and rec["c"] > 0)
    except Exception as e:  # pragma: no cover - defensive
        logger.warning("seed: could not check seed graph population: %s", e)
        return False


def _total_node_count(storage) -> Optional[int]:
    try:
        with storage._driver.session() as session:
            rec = session.run("MATCH (n) RETURN count(n) AS c").single()
            return int(rec["c"]) if rec else 0
    except Exception as e:
        logger.warning("seed: could not count nodes (Neo4j not ready?): %s", e)
        return None


def ensure_seed_graph(storage) -> Optional[str]:
    """Load the static demo graph iff the database is empty.

    Returns the seed ``graph_id`` when the seed graph is present (either
    already there, or freshly loaded), otherwise ``None``. Never raises.
    """
    if storage is None:
        return None

    # Already populated? Honour the strict "only when count == 0" gate so we
    # never touch a judge's existing/customer graph.
    if seed_graph_has_entities(storage):
        logger.info("seed: seed graph %s already present — skipping", SEED_GRAPH_ID)
        return SEED_GRAPH_ID

    total = _total_node_count(storage)
    if total is None:
        return None  # Neo4j not reachable yet; Posture B will handle sim time.
    if total > 0:
        logger.info(
            "seed: database already has %d node(s) and no seed graph — "
            "leaving as-is (no clobber)",
            total,
        )
        return None

    try:
        fixture = _load_fixture()
    except Exception as e:
        logger.error("seed: failed to read fixture %s: %s", _FIXTURE_PATH, e)
        return None

    now = datetime.now(timezone.utc).isoformat()
    nodes = [
        {
            "uuid": n["uuid"],
            "name": n["name"],
            "name_lower": n["name"].lower(),
            "label": n["label"],
            "summary": n.get("summary", ""),
        }
        for n in fixture.get("nodes", [])
    ]
    edges = [
        {
            "uuid": e["uuid"],
            "source": e["source"],
            "target": e["target"],
            "name": e["name"],
            "fact": e.get("fact", ""),
        }
        for e in fixture.get("edges", [])
    ]

    def _write(tx):
        tx.run(
            """
            MERGE (g:Graph {graph_id: $gid})
            SET g.name = $name,
                g.description = $description,
                g.ontology_json = coalesce(g.ontology_json, '{}'),
                g.created_at = coalesce(g.created_at, $now)
            """,
            gid=SEED_GRAPH_ID,
            name=fixture.get("graph_name", "Bags demo seed"),
            description=fixture.get("graph_description", ""),
            now=now,
        )
        # Static labels come only from this committed fixture (not user
        # input); APOC keeps the dynamic label set clean.
        tx.run(
            """
            UNWIND $nodes AS n
            MERGE (e:Entity {uuid: n.uuid})
            SET e.graph_id = $gid,
                e.name = n.name,
                e.name_lower = n.name_lower,
                e.summary = n.summary,
                e.attributes_json = '{}',
                e.created_at = $now
            WITH e, n
            CALL apoc.create.addLabels(e, [n.label]) YIELD node
            RETURN count(node)
            """,
            nodes=nodes,
            gid=SEED_GRAPH_ID,
            now=now,
        )
        tx.run(
            """
            UNWIND $edges AS rel
            MATCH (s:Entity {uuid: rel.source})
            MATCH (t:Entity {uuid: rel.target})
            MERGE (s)-[r:RELATION {uuid: rel.uuid}]->(t)
            SET r.graph_id = $gid,
                r.name = rel.name,
                r.fact = rel.fact,
                r.attributes_json = '{}',
                r.created_at = $now
            """,
            edges=edges,
            gid=SEED_GRAPH_ID,
            now=now,
        )

    try:
        with storage._driver.session() as session:
            storage._call_with_retry(session.execute_write, _write)
    except Exception as e:
        logger.error("seed: failed to load static seed graph: %s", e)
        return None

    logger.info(
        "seed: loaded static demo graph %s (%d personas, %d relations) — "
        "synthetic data only",
        SEED_GRAPH_ID,
        len(nodes),
        len(edges),
    )
    return SEED_GRAPH_ID
