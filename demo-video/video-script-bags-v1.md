# Monitor × MiroShark — Bags Hackathon Demo Script (v1)

**Target length:** 2:30
**Format:** AI-generated B-roll (Replicate/Seedance or Veo) + live screen recordings + AI voiceover
**Tone:** Cinematic hook, then technical and punchy. Real product, real simulation, real Solana USDC settlement.
**Narrative axis:** Bags.fm token launches → Monitor detects anomaly → MiroShark swarm simulates reaction → Quartz graph explains consensus → Solana x402 payment unlocks the analysis.

---

## SECTION 1 — Hook (0:00–0:12) [12s]

**[VIDEO — cinematic B-roll]**
Fast zoom across a neon Solana-colored token feed; a single token spikes green then red; camera whip-pans into a dark terminal.

**Narration:**
> "A new token just launched on Bags.fm. Thirty seconds later it's up 400%. Thirty seconds after that, it's rugged. Humans can't keep up — but an AI swarm can."

*On-screen overlay:* `bags.fm launches // 30s rug cycle // humans out of the loop`

---

## SECTION 2 — Monitor Detects (0:12–0:40) [28s]

**[SCREEN RECORDING — Monitor dashboard]**
- Live Bags.fm feed streaming token launches.
- A composite risk score ticks up on one token (pool depth, lifetime fees, price trajectory, velocity) — gauges flip green → amber → red.
- Zoom into the anomaly row.

**Narration:**
> "Meet Monitor the Situation — an autonomous agent watching the entire Bags.fm firehose, live."

> "Four signals: pool liquidity, lifetime fees, price trajectory, and launch velocity. When the composite risk score crosses threshold, Monitor doesn't just alert — it triggers a deep analysis."

*On-screen overlays:* `composite risk // 4 signals // pool + fees + price + velocity // threshold → deep analysis`

---

## SECTION 3 — MiroShark Swarm Simulates (0:40–1:15) [35s]

**[VIDEO / SCREEN — swarm visualization + Quartz preview]**
- AI-generated swarm clip (hundreds of agent nodes lighting up across simulated Twitter / Reddit / Polymarket / Bags.fm).
- Cut to Quartz graph view: persona cards (momentum trader, whale-tracker, contrarian, shiller, conservative analyst), edges showing who influences whom.

**Narration:**
> "Monitor fires the token into MiroShark — a multi-agent swarm grounded in a Neo4j knowledge graph."

> "Hundreds of LLM personas — momentum traders, whale-trackers, contrarians, shillers, conservative analysts — debate the launch across simulated Twitter, Reddit, Polymarket, and Bags.fm itself."

> "Each persona has five layers of context: graph attributes, relationships, semantic search, related nodes, and live web research. Beliefs propagate across platforms. Rounds compact into summaries so long simulations stay coherent."

*On-screen overlays:* `100s of personas // 5-layer grounding // cross-platform belief propagation`

---

## SECTION 4 — Explainable Consensus (1:15–1:45) [30s]

**[SCREEN RECORDING — Quartz graph view]**
- Navigate the agent network: click a persona, see its belief trajectory over rounds.
- Highlight cluster convergence; show the ReACT report agent's final consensus card.

**Narration:**
> "Every stance, every confidence update, every debate — rendered as a navigable Quartz graph."

> "You can trace exactly why the swarm converged: which persona moved first, who followed, which arguments flipped the room. Explainable AI, not a black box."

*On-screen overlays:* `Quartz graph // navigable swarm // every belief traced`

---

## SECTION 5 — Agent-Native Payments on Solana (1:45–2:15) [30s]

**[SCREEN RECORDING — terminal + Solana explorer]**
- `curl` the deep-analysis endpoint → `402 Payment Required`.
- Sign USDC micropayment on Solana devnet with x402.
- `200 OK` — full JSON analysis drops in the terminal.
- Cut to Solana Explorer showing the on-chain transaction.

**Narration:**
> "And the whole thing is paywalled — not with API keys, but with agent-native payments."

> "Every endpoint speaks x402, the HTTP payment protocol. Hit it unpaid — 402. Sign a USDC micropayment on Solana devnet — 200, full analysis JSON. Autonomous agents can pay each other, per request, on-chain."

*On-screen overlays:* `x402 // USDC on Solana devnet // pay-per-call // no API keys`

---

## SECTION 6 — Close (2:15–2:30) [15s]

**[VIDEO — cinematic outro]**
Camera pulls back from the Quartz graph into a Solana-colored globe; the `Monitor × MiroShark` wordmark lands with the Zero Human Labs signature.

**Narration:**
> "Monitor the Situation. MiroShark swarm intelligence. Agent-native payments. All on Solana."

> "Built by Zero Human Labs — where every employee is an AI agent."

*On-screen overlay:* `github.com/Zoidberg-eternal/monitor-the-situation-stellar // Zero Human Labs // Bags Hackathon 2026`

---

## VOICEOVER SCRIPT (clean, for TTS)

> A new token just launched on Bags.fm. Thirty seconds later it's up four hundred percent. Thirty seconds after that, it's rugged. Humans can't keep up — but an AI swarm can.
>
> Meet Monitor the Situation — an autonomous agent watching the entire Bags.fm firehose, live. Four signals: pool liquidity, lifetime fees, price trajectory, and launch velocity. When the composite risk score crosses threshold, Monitor doesn't just alert — it triggers a deep analysis.
>
> Monitor fires the token into MiroShark — a multi-agent swarm grounded in a Neo4j knowledge graph. Hundreds of LLM personas — momentum traders, whale-trackers, contrarians, shillers, conservative analysts — debate the launch across simulated Twitter, Reddit, Polymarket, and Bags.fm itself. Each persona has five layers of context: graph attributes, relationships, semantic search, related nodes, and live web research. Beliefs propagate across platforms. Rounds compact into summaries so long simulations stay coherent.
>
> Every stance, every confidence update, every debate — rendered as a navigable Quartz graph. You can trace exactly why the swarm converged: which persona moved first, who followed, which arguments flipped the room. Explainable AI, not a black box.
>
> And the whole thing is paywalled — not with API keys, but with agent-native payments. Every endpoint speaks x402, the HTTP payment protocol. Hit it unpaid — four-oh-two. Sign a USDC micropayment on Solana devnet — two hundred, full analysis JSON. Autonomous agents can pay each other, per request, on-chain.
>
> Monitor the Situation. MiroShark swarm intelligence. Agent-native payments. All on Solana. Built by Zero Human Labs — where every employee is an AI agent.

**Approx word count:** ~290 words — ~1:55 at 150 wpm, fits with music/B-roll gaps inside 2:30.

---

## SHOT LIST

| # | Source | Duration | Notes |
|---|---|---|---|
| 1 | AI-gen (new) — "Bags.fm token feed → green spike → red rug" | 8s | Neon Solana palette. Replicate/Seedance or Veo prompt below. |
| 2 | Screen recording (new) — Monitor dashboard, Bags.fm feed | 10s | Need live Docker Compose stack + anomaly trigger on a real token. |
| 3 | Screen recording (new) — composite risk gauge flipping | 8s | Four gauges stacked, amber → red transition. |
| 4 | Reuse — `section3-swarm.mp4` (existing) | 5s | Generic swarm clip still fits. |
| 5 | Screen recording (new) — Quartz graph navigation | 15s | Click-through a persona, show belief trajectory. |
| 6 | Screen recording (new) — Quartz cluster + ReACT report | 10s | Consensus card close-up. |
| 7 | Screen recording (new) — terminal curl 402 → pay → 200 | 15s | `solana-gateway` in Docker, devnet wallet. |
| 8 | Screen recording (new) — Solana Explorer tx view | 8s | Show on-chain settlement. |
| 9 | AI-gen (new) — cinematic outro, Solana globe + wordmark | 8s | Replicate/Seedance or Veo prompt below. |

**Reuse candidates from prior Stellar video (`demo-video/`):**
- `section1-intro.mp4` — maybe reusable as hook if retinted Solana-purple.
- `section3-swarm.mp4` — reusable as-is.
- `globe-broll.mp4` — reusable for outro.
- All `grok-*.mp4` clips (maritime/oilfield/trading floor) — **not reusable** (wrong narrative).
- All `section2*` / `section4-x402.mp4` — **not reusable** (Stellar-branded, wrong endpoints).

---

## AI VIDEO GENERATION PROMPTS (new clips)

**Shot 1 — Bags.fm feed / rug cycle (8s):**
> Cinematic close-up of a dark neon trading dashboard, streaming token feed scrolling top to bottom in Solana purple and teal. One row pulses green, shoots a candle chart upward with particle effects, then flashes red and collapses. Ultra-high detail, 4K, shallow depth of field, subtle film grain.

**Shot 9 — Outro (8s):**
> Slow pull-back from a navigable 3D agent network (glowing purple nodes, teal edges) into a globe rendered in the Solana palette. Particles converge into the wordmark "Monitor × MiroShark" which lands center-frame, followed by "Zero Human Labs" in smaller type. Cinematic, dark background, 4K.

---

## PRODUCTION PLAN — ORDER OF OPERATIONS

1. **Voiceover** — generate from the TTS block above (OpenAI `tts-1` or ElevenLabs). Target ~1:55, leave room for breath gaps and music swells.
2. **Screen recordings** — record on a Mac with the stack running:
   - `docker compose up` → wait for healthy Monitor + MiroShark + Neo4j + solana-gateway.
   - Trigger a deep analysis on a real Bags.fm token (use script from ZERA-497).
   - QuickTime or OBS, 1080p, 60fps.
3. **AI clips** — generate Shots 1 and 9 via Replicate Seedance Lite (same pipeline as prior video) or Veo 3.1. Requires `REPLICATE_API_TOKEN`.
4. **Normalize** — `ffmpeg` pass to force 1920x1080, 30fps, stereo AAC 48k, H.264.
5. **Stitch** — concat with `ffmpeg -f concat` (see `concat-v6.txt` as template).
6. **Mix** — add voiceover on audio track 2, music bed (`music.mp3`) ducked to -18dB under VO.
7. **Overlays** — use `ffmpeg drawtext` for the on-screen stats; export title/end cards as PNG.
8. **Export** — `monitor-miroshark-bags-FINAL.mp4` at 1080p, H.264, 8–12 Mbps.
9. **Upload** — YouTube, "Monitor × MiroShark — Bags Hackathon Demo", public, copy URL into `SUBMISSION.md` line 66.

---

## KEY STATS (for overlays)

- `100s of personas per simulation`
- `4-signal composite risk score`
- `5-layer persona grounding (graph, relationships, semantic, related, web)`
- `USDC on Solana devnet via x402`
- `Explainable swarm — every belief traced in Quartz`

---

## REUSABLE ASSETS ALREADY IN `demo-video/`

- `music.mp3` — existing music bed, reusable.
- `voiceover.mp3` / `voiceover-short.mp3` — **old Stellar narration, do not reuse**.
- `section3-swarm.mp4` — reusable as-is.
- `globe-broll.mp4` — reusable for outro B-roll.
- `concat-v6.txt` — use as the template for the new concat file.

---

## FINAL FILENAME

Target: `demo-video/monitor-miroshark-bags-FINAL.mp4` (relative to the repo root)
