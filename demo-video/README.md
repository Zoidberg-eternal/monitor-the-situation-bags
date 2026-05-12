# Monitor × MiroShark — Bags Hackathon Demo Video

The submission cut for the [Bags Hackathon](https://dorahacks.io/hackathon/the-bags-hackathon/detail) lives here.

- **Final cut:** [`monitor-miroshark-bags-FINAL.mp4`](./monitor-miroshark-bags-FINAL.mp4) · 1920×1080 @ 30 fps · ~1:45 · H.264 / AAC
- **Voiceover-only mix:** `voiceover-bags.mp3`
- **Script (locked):** [`video-script-bags-v1.md`](./video-script-bags-v1.md)
- **Rebuildable pipeline:** `build-final-bags.sh` + `concat-bags-final.txt` + `build-overlay-cards.py --final`
- **Stand-in build (kept for reference):** [`monitor-miroshark-bags-ROUGHCUT-v1.mp4`](./monitor-miroshark-bags-ROUGHCUT-v1.mp4)

The submission is tracked in [SUBMISSION.md](../SUBMISSION.md) (parent: ZERA-499).

---

## What's real in the video, what's a purpose-built UI

To keep the 1:45 walkthrough deterministic and readable, three of the on-screen surfaces in the video are **demo-specific UIs built on top of the real backend**, not the production frontends. Everything they show is faithful to the live system's data model and response shapes; the visual shell is purpose-built so the Bags.fm narrative reads cleanly on screen.

### Monitor risk console (Shots 2 + 3 — `0:05–0:33`)

The Monitor risk console shown is a UI built for this demo on top of the live Monitor API (`monitor/server.py`, FastAPI on port `:8402`). The token feed, four-signal composite risk score (pool liquidity, lifetime fees, price trajectory, launch velocity), anomaly log, and the SAFE → WATCH → RISK gauge transitions are all real Monitor behaviour. The visual console (`playwright-recorder/dashboard-mock/index.html`) is a styled HTML shell wired to the same data model so the gauge flip and anomaly pulse are frame-accurate.

### Quartz knowledge-graph view (Shots 5 + 6 — `0:43–1:03`)

The Quartz graph + ReACT consensus view shown is a UI built for this demo (`playwright-recorder/quartz-mock/index.html`) reflecting MiroShark's real swarm primitives. The eight persona archetypes (momentum-trader, whale-tracker, contrarian, shiller, conservative-analyst, reddit-degen-radar, polymarket-arb, x-influencer-tracker), 5-layer grounding, belief-trajectory schema, cluster-convergence model, and ReACT consensus report are real features of the swarm runtime — they are what the live `quartz-monitor/` site renders against actual simulation runs. We rebuilt the visual shell for the demo so the WIRED-launch narrative reads in 20 seconds; the live site shows the same primitives against whatever simulation is loaded.

### Scripted terminal — x402 payment (Shot 7 — `1:03–1:21`)

The terminal `curl` → `402` → sign → `200` exchange is scripted against the real x402 / Solana gateway response shape (`playwright-recorder/terminal-mock/index.html`). The 402 headers, the x402 payment payload, the signature broadcast call, and the 200 + JSON analysis body all match what the live `solana-gateway:3403` returns when you exercise it on devnet. The visual terminal is scripted purely so the typing cadence and timing land on beat with the voiceover.

---

## What's the real product (no mock)

- **Monitor API** — `monitor/server.py`, FastAPI on `:8402`. Composite-risk scoring, anomaly detection, deep-analysis trigger logic.
- **MiroShark swarm runtime** — multi-agent swarm grounded in a Neo4j knowledge graph. Personas, 5-layer grounding, ReACT consensus.
- **`solana-gateway`** — x402 HTTP-payment gateway, USDC settlement on Solana devnet. Container at port 3403 per `docker-compose.yml`.
- **Quartz knowledge-graph site** — `quartz-monitor/quartz-site/` renders the live simulation graph at `localhost:8001`. The video's mock mirrors this site's primitives against the Bags.fm narrative.
- **Section 3 / MiroShark swarm B-roll** (`0:33–0:43`) — generic AI b-roll, not a UI capture.
- **Section 9 / Solana globe outro** (`1:33–1:45`) — generic AI b-roll, not a UI capture.

---

## How to rebuild the final cut

```bash
cd demo-video

# 1. Regenerate the 1080p caption PNGs (idempotent).
python3 build-overlay-cards.py --final

# 2. If you re-recorded any shot, drop it into raw-recordings/ as
#    raw-shotN-<slug>.{mov,mp4,mkv}. The build cache invalidates on mtime.

# 3. Re-render. Single command, end to end. Cached normalize steps are skipped.
./build-final-bags.sh
```

Outputs `monitor-miroshark-bags-FINAL.mp4` in this directory.

To re-record the Monitor / Quartz / terminal mocks against the same Playwright recorders:

```bash
cd demo-video/playwright-recorder

# Serve each mock on its dedicated port:
python3 -m http.server 8002 --bind 127.0.0.1 --directory dashboard-mock &
python3 -m http.server 8003 --bind 127.0.0.1 --directory terminal-mock &
python3 -m http.server 8004 --bind 127.0.0.1 --directory quartz-mock &

# Record (each emits a 1920×1080 webm into videos-shotN/):
node record-shot2-dashboard.js
node record-shot3-risk-gauge.js
node record-shot5-quartz-navigate-v2.js
node record-shot6-quartz-cluster-v2.js
node record-shot7-terminal.js
node record-shot8-explorer.js

# Convert webm → mp4 and drop into ../raw-recordings/ for the build.
```

---

## Caption timing reference

The final cut's caption windows are tuned for the actual ~1:45 timeline. See the comment block in `build-final-bags.sh` next to the overlay filter for the cumulative shot boundaries.

| Caption | Window | Lands on |
|---|---|---|
| `BAGS.FM // 30s rug cycle // humans out of the loop` | 0–5 s | Shot 1 — intro |
| `MONITOR // 4-signal composite risk` | 8–18 s | Shot 2 — dashboard |
| `MIROSHARK // 100s of personas // 5-layer grounding` | 34–42 s | Shot 4 — swarm |
| `QUARTZ graph // every belief traced` | 44–54 s | Shot 5 — Quartz |
| `x402 // USDC on Solana devnet // pay-per-call` | 65–75 s | Shot 7 — terminal |
| Outro full-frame title | 94–102.7 s | Shot 9 — Solana globe outro |
