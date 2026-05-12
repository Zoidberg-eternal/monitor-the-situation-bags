# quartz-monitor

Interactive Quartz graph view of MiroShark simulation data for "Monitor the Situation".

## Structure

- `scripts/export-to-quartz.py` — Exports MiroShark simulation data (SQLite DBs, JSONL actions, CSV profiles, trajectory JSON) to Obsidian-style markdown with wikilinks.
- `quartz-site/` — Quartz 4 static site, customized with "Monitor the Situation" branding.
- `content/` — Latest snapshot of generated markdown (also copied into `quartz-site/content/` at build time).
- `build.sh` — One-command re-export + rebuild.

## Content layout

```
content/
├── index.md                    # Dashboard overview
├── agents/                     # One page per simulation agent (persona + belief trajectory + quotes)
├── tokens/                     # One page per asset (BTC, ETH, SOL, oil, gold, silver, natural gas)
├── simulations/                # Per-sim summary pages
└── rounds/                     # Per-round detail pages
```

## First-time setup

```bash
cd quartz-site
npm install
```

## Build + serve

From the project root:

```bash
./build.sh                                # re-export content and build
cd quartz-site && npx quartz build --serve  # serve on http://localhost:8080
```

## Data source

Reads from `$MIROSHARK_SIMS_DIR` (defaults to `miroshark/backend/uploads/simulations/` relative to the working directory). Set the env var, or update the `SIMS_DIR` constant in `scripts/export-to-quartz.py`.
