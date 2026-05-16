"""Static demo-graph seeding for the one-command judge path (ZERA-600).

Exposes :data:`SEED_GRAPH_ID` and :func:`ensure_seed_graph`.
"""

from .seed_loader import SEED_GRAPH_ID, ensure_seed_graph

__all__ = ["SEED_GRAPH_ID", "ensure_seed_graph"]
