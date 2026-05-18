# Vendored MiroShark — pin & provenance

Pinned, verbatim vendor so the documented one-command judge path works from a
single fresh clone with **zero extra steps** (ZERA-600 / ZERA-499).

| Field | Value |
|-------|-------|
| Upstream | https://github.com/aaronjmars/MiroShark |
| Vendored commit (pin) | `abdadd9db760e5ec06ff6887e573d1fe92b0dd90` |
| Vendored branch | `zera-600-static-seed` |
| License | **AGPL-3.0** — see `./LICENSE` and `./NOTICE` |
| Vendored at | 2026-05-18 |

## Contents (ZERA-600)
- Posture-A static **synthetic** seed (`backend/app/seed/bags_demo_graph.json`, 10 personas, no customer data).
- Posture-B enumerated degradation incl. OOM-mid-sim (`backend/app/services/degradation.py`).
- 3(b) deterministic consensus test + faithful reddit trace->AgentAction adapter test.
- Demo preset knobs: MIROSHARK_DEMO_MAX_PERSONAS, MIROSHARK_SIM_PLATFORM (default reddit),
  WONDERWALL_DEFAULT_MAX_ROUNDS — the documented default; opt out for the heavy parallel run.

## Reproduce / re-pin
```
git clone https://github.com/aaronjmars/MiroShark && cd MiroShark
git checkout abdadd9db760e5ec06ff6887e573d1fe92b0dd90 && git archive HEAD | tar -x -C <bags>/miroshark
```
Bump the pin deliberately (record new commit here) — never mutate in place.
