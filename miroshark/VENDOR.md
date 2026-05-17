# Vendored MiroShark — pin & provenance

Pinned, verbatim vendor of MiroShark so the documented one-command judge
path works from a single fresh clone with **zero extra steps**
(ZERA-600 / ZERA-499, acceptance AC1/AC6).

| Field | Value |
|-------|-------|
| Upstream | https://github.com/aaronjmars/MiroShark |
| Vendored commit (pin) | `59e8528dd63202885bf792d3af0552b1ca0be2c0` |
| Vendored branch | `zera-600-static-seed` |
| License | **AGPL-3.0** — see `./LICENSE` and `./NOTICE` |
| Vendored at | 2026-05-17 |

## Contents
Exact tracked tree at the pin (via `git archive`) — no `.git`, `.venv`,
`node_modules`, `__pycache__`. Includes ZERA-600:
- Posture-A static **synthetic** seed (`backend/app/seed/bags_demo_graph.json`
  — 10 personas, no customer data/hashes).
- Posture-B enumerated degradation (`backend/app/services/degradation.py`)
  incl. OOM-mid-sim `simulation_incomplete_resource`.
- 3(b) deterministic consensus-aggregation test
  (`backend/tests/test_unit_zera600_consensus.py`).

## Reproduce / re-pin
```
git clone https://github.com/aaronjmars/MiroShark
cd MiroShark && git checkout 59e8528dd63202885bf792d3af0552b1ca0be2c0
git archive HEAD | tar -x -C <bags>/miroshark
```
Bump the pin deliberately (record the new commit here) — never mutate in place.
