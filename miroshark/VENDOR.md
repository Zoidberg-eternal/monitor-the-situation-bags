# Vendored MiroShark — pin & provenance

This directory is a **pinned, verbatim vendor** of the MiroShark service so the
documented one-command judge path works from a single fresh clone of
`monitor-the-situation-bags` with **zero extra steps** (ZERA-600 / ZERA-499,
acceptance criteria AC1/AC6).

| Field | Value |
|-------|-------|
| Upstream | https://github.com/aaronjmars/MiroShark |
| Vendored commit (pin) | `fc07991999dced7940010cfcf1285f817de335d9` |
| Vendored branch | `zera-600-static-seed` (includes the ZERA-600 static synthetic seed) |
| License | **AGPL-3.0** — see `./LICENSE` and `./NOTICE` |
| Vendored at | 2026-05-16 |

## What is included
The exact tracked tree at the pin above (via `git archive`) — no `.git`,
`.venv`, `node_modules`, or `__pycache__`. This includes the ZERA-600
Posture-A static seed (`backend/app/seed/bags_demo_graph.json` — 10 **synthetic**
personas, no customer data/hashes) and Posture-B graceful degradation.

## Reproducing / re-pinning
```
git clone https://github.com/aaronjmars/MiroShark
cd MiroShark && git checkout fc07991999dced7940010cfcf1285f817de335d9
# apply the ZERA-600 seed branch (zera-600-static-seed) if re-deriving
git archive HEAD | tar -x -C <bags>/miroshark
```
Bump the pin deliberately (new commit recorded here) — never mutate in place.
