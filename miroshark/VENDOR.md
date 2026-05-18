# Vendored MiroShark — pin & provenance

Pinned, verbatim vendor of MiroShark so the documented one command works
from a single fresh clone with zero extra steps (ZERA-600 / ZERA-499).

| Field | Value |
|-------|-------|
| Upstream | https://github.com/aaronjmars/MiroShark |
| Vendored commit (pin) | `8f16de44d8923d6cb463a4fc83a3ac0ec9e54985` |
| Vendored branch | `zera-600-static-seed` |
| License | **AGPL-3.0** — see `./LICENSE` and `./NOTICE` |
| Vendored at | 2026-05-17 |

## Contents (ZERA-600)
- Posture-A static **synthetic** seed (10 personas, no customer data).
- Posture-B enumerated degradation incl. OOM-mid-sim
  `simulation_incomplete_resource`; corrected memory remediation.
- 3(b) deterministic consensus-aggregation test.
- Demonstrative-preset knobs: `MIROSHARK_DEMO_MAX_PERSONAS`,
  `MIROSHARK_SIM_PLATFORM`, `WONDERWALL_DEFAULT_MAX_ROUNDS`.

## Reproduce / re-pin
```
git clone https://github.com/aaronjmars/MiroShark
cd MiroShark && git checkout 8f16de44d8923d6cb463a4fc83a3ac0ec9e54985
git archive HEAD | tar -x -C <bags>/miroshark
```
