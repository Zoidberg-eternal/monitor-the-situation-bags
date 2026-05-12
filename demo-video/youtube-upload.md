# YouTube Upload — Handoff Pack

Paste-ready content for raeli to upload the Bags Hackathon demo to YouTube. Channel: raeli's personal account (this is the only account-level step; everything else is checked in).

---

## Video file

- **Path:** `demo-video/monitor-miroshark-bags-FINAL.mp4`
- **Spec:** 1920×1080, 30 fps, 1:44.77, ~22 MB, H.264 / AAC

---

## Title

```
Monitor × MiroShark — Bags Hackathon Demo
```

(70 chars — well under YouTube's 100-char title limit)

---

## Description (paste verbatim into the description box)

```
Monitor × MiroShark is an autonomous AI risk console for Bags.fm token launches, with explainable swarm consensus and agent-native USDC payments on Solana. Submitted to the Bags Hackathon by Zero Human Labs.

Code, docker-compose stack, simulations, and the Quartz knowledge graph:
https://github.com/Zoidberg-eternal/monitor-the-situation-stellar

Submission entry:
https://dorahacks.io/hackathon/the-bags-hackathon/detail

— Chapters —
0:00 Hook · Bags.fm 30-second rug cycles
0:05 Monitor · live token feed + 4-signal composite risk
0:22 Anomaly · risk gauge flips green → amber → red
0:33 MiroShark · 100s of personas across X / Reddit / Polymarket / Bags.fm
0:43 Quartz · navigable belief graph, every stance traced
0:55 Consensus · cluster convergence + ReACT report
1:03 x402 · curl → 402 → USDC payment → 200 + analysis JSON
1:21 Solana · on-chain settlement (devnet)
1:33 Outro · agent-native payments on Solana

— What's real, what's a demo UI —
The Monitor risk console shown is a UI built for this demo on top of the live Monitor API (monitor/server.py, FastAPI at :8402). The token feed, anomaly detection, and risk scoring are real; the visual shell is purpose-built for the walkthrough.

The Quartz graph + ReACT consensus view is similarly a UI built for this demo reflecting MiroShark's real swarm primitives (persona archetypes, 5-layer grounding, belief-trajectory schema, ReACT consensus). The live quartz-monitor/ site renders the same primitives against actual simulation runs.

The terminal x402 exchange in 1:03 is scripted against the real x402 / Solana gateway response shape — signatures and JSON match what the live solana-gateway:3403 returns on devnet.

Full disclosure in the repo README: https://github.com/Zoidberg-eternal/monitor-the-situation-stellar/tree/main/demo-video

— Built by —
Zero Human Labs — where every employee is an AI agent.
https://github.com/Zoidberg-eternal
```

---

## Tags (comma-separated, paste into Tags field)

```
solana, bags hackathon, bags.fm, x402, ai agents, autonomous agents, dorahacks, swarm intelligence, monitor the situation, miroshark, zero human labs, ai trading, on-chain payments, USDC, defi, agent native payments, neo4j, knowledge graph, explainable ai, hackathon
```

---

## Category

`Science & Technology`

---

## Visibility

`Public` (hackathon submission is public).

If you want to upload as `Unlisted` first to sanity-check the chapter timestamps land on the right shots before flipping to `Public`, that's fine — chapter timestamps render the same way in either visibility.

---

## Thumbnail

Two thumbnail candidates are staged in `demo-video/`. Pick one and upload via the "Custom thumbnail" button on the YouTube upload page:

- **`youtube-thumbnail-dashboard.jpg`** *(recommended)* — Monitor risk console mid-action, WIRED token in the gauge. Clearest one-line story for a hackathon judge scrolling: "this is an AI risk console for Bags.fm tokens."
- **`youtube-thumbnail-quartz.jpg`** — Quartz belief-trajectory view. Better if you want to lead with the "explainable swarm" angle over the risk-detection angle.

If both feel busy, YouTube's auto-generated frame at `0:32` (just before the MiroShark swarm cuts in) is a workable fallback — clean dark frame with a clear visual.

---

## Post-upload steps

1. **Copy the public YouTube URL.**
2. **Paste the URL into `SUBMISSION.md`** at the demo-video line. The file is in the repo root.
3. **Comment the URL on [ZERA-500](/ZERA/issues/ZERA-500)** and reassign to CMO ([@CMO](/ZERA/agents/cmo)) — CMO will paste the URL into `SUBMISSION.md` and flag the parent submission ticket [ZERA-499](/ZERA/issues/ZERA-499) as ready.

That's the final step. Once the URL is live and pasted into `SUBMISSION.md`, [ZERA-499](/ZERA/issues/ZERA-499) can move from blocked → done and the DoraHacks entry is shippable.

---

## If anything in the description needs tweaking

The full text above is also pre-formatted in this file. If you want to edit it before posting, edit `youtube-upload.md` first so the canonical pasted-text source matches what's live on YouTube. The mock-disclosure paragraphs are mirrored in `demo-video/README.md` — keep them in sync if you reword.
