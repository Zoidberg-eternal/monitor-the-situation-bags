# Monitor × MiroShark — Bags Demo Production Handoff

**Target (final):** `demo-video/monitor-miroshark-bags-FINAL.mp4` — 2:00–2:30, 1080p, H.264, ~8–12 Mbps.
**Preview cut available now:** `demo-video/monitor-miroshark-bags-ROUGHCUT-v1.mp4` — 1:55.9, 720p, watermarked "ROUGH CUT v1 - stand-in visuals". Watchable end-to-end with the locked Bags voiceover, music bed, and Bags-narrative captions — but visuals for Shots 2/3/5/6/7/8 are AI b-roll stand-ins, not the live Monitor/Quartz/x402 stack. Use this for narrative review only.
**Script (locked):** `demo-video/video-script-bags-v1.md`.
**Voiceover (ready):** `demo-video/voiceover-bags.mp3` — OpenAI `tts-1-hd`, voice `onyx`, 104s, 160 kbps mono.

---

## What's done

- ✅ Locked script (ZERA-500 Reddit Marketer heartbeat).
- ✅ TTS voiceover generated — `voiceover-bags.mp3`, 1:44 runtime, leaves ~46s of music/B-roll space inside 2:30.
- ✅ Music bed exists — `music.mp3`.
- ✅ Reusable clips confirmed in `demo-video/`:
  - `section3-swarm.mp4` — swarm shot (Shot 4 slot).
  - `globe-broll.mp4` — outro globe B-roll (Shot 9 fallback if AI re-gen is skipped).
- ✅ **Rough-cut v1 stitched, mixed, exported** — `monitor-miroshark-bags-ROUGHCUT-v1.mp4` (1:55.9, 720p, AAC mono, ~67 MB). Concat list: `concat-bags-roughcut-v1.txt`. Build script: `build-roughcut-bags-v1.sh`. Overlay cards: `ovl-01-hook.png` … `ovl-07-watermark.png` (regen via `python3 build-overlay-cards.py`).
- ✅ Pipeline validated end-to-end: concat → multi-overlay PNGs → VO+ducked-music mix → H.264 export. Same chain re-runs once raw screen recordings replace the stand-in segments.
- ✅ **Final-cut pipeline pre-staged (1080p):** `build-final-bags.sh` + `concat-bags-final.txt` + 1080p mode in `build-overlay-cards.py --final`. After the six raw shots land in `demo-video/` (or `demo-video/raw-recordings/`), the final cut is a single command — see "Ready-to-run stitch/mix commands" below.

## Stand-in slots in the rough cut (must be replaced for final)

The rough cut covers each script section with stock/abstract AI b-roll — visually fine for narrative pacing review, but **not** representative of the actual product. These slots must be replaced with live recordings before the final upload:

| Rough-cut timecode | Stand-in clip(s) used | Must be replaced with |
|---|---|---|
| 0:11 – 0:33 | `norm-section2-terminal.mp4`, `norm-section2b-dashboard.mp4`, `norm-grok-oilfield.mp4` | Shot 2 (Monitor dashboard, Bags.fm feed) + Shot 3 (composite risk gauge flip) |
| 1:06 – 1:22 | `norm-globe.mp4`, `norm-section1-intro.mp4` | Shot 5 (Quartz graph navigation) + Shot 6 (cluster + ReACT consensus) |
| 1:23 – 1:38 | `norm-section4-x402.mp4` ×2, `norm-section5-outro.mp4` | Shot 7 (terminal x402 402→pay→200) + Shot 8 (Solana Explorer tx) |
| 0:00 – 0:06 / 1:43 – 1:55 | `norm-grok-tradingfloor.mp4` / `norm-globe-broll-720.mp4` | Optional AI re-gen of Shots 1 + 9 if `REPLICATE_API_TOKEN` available |

## What's still needed (human / GUI-capable agent)

| Blocker | Who can do it | Est. effort |
|---|---|---|
| Shot 1 — AI B-roll (Bags.fm feed → rug cycle, 8s) | Anyone with `REPLICATE_API_TOKEN` or Veo/Sora access | 10 min |
| Shot 9 — AI B-roll (Solana globe + wordmark, 8s) | Same | 10 min (OR reuse `globe-broll.mp4` + text overlay) |
| Shot 2 — Monitor dashboard live feed | Human on Mac, Docker stack up | 15 min |
| Shot 3 — Composite risk gauge flip | Same session | 10 min |
| Shot 5 — Quartz graph navigation | Same session | 15 min |
| Shot 6 — Quartz cluster + ReACT consensus | Same session | 10 min |
| Shot 7 — Terminal `curl` 402 → pay → 200 | Same session, devnet wallet loaded | 10 min |
| Shot 8 — Solana Explorer tx view | Same session | 5 min |
| YouTube upload + URL into `SUBMISSION.md` L66 | Account owner | 5 min |

Total operator time: ~1.5 hours end-to-end. Agent (me) can take over at "stitch + mix + export" once raw assets land in `demo-video/`.

---

## Exact step-by-step — screen recording session

1. **Bring up the stack**

   ```bash
   cd <repo-root>
   docker compose up -d
   # wait for healthy: monitor, miroshark, neo4j, solana-gateway
   docker compose ps
   ```

2. **Set up OBS / QuickTime** — 1920×1080, 30fps, record only the Monitor/Quartz browser window and Terminal. Save raw recordings into `demo-video/raw-recordings/` with names matching the shot list below.

3. **Record each shot** (raw filenames expected by the stitch step):

   | File | What to capture |
   |---|---|
   | `raw-shot2-dashboard.mov` | Monitor dashboard — Bags.fm feed scrolling, risk gauges visible. Zoom on anomaly row. 10s. |
   | `raw-shot3-risk-gauge.mov` | Close-up on composite risk gauge as it moves green → amber → red on a real token. 8s. |
   | `raw-shot5-quartz-navigate.mov` | Quartz graph — click a persona node, hover edges, show belief trajectory panel. 15s. |
   | `raw-shot6-quartz-report.mov` | Quartz cluster view + ReACT report agent consensus card. 10s. |
   | `raw-shot7-terminal-x402.mov` | Terminal: `curl` deep-analysis endpoint → 402, sign USDC payment via x402 client, re-call → 200 with JSON. 15s. |
   | `raw-shot8-solana-explorer.mov` | Explorer showing the on-chain USDC transaction. 8s. |

4. **(Optional) AI re-gen for Shots 1 + 9** — if `REPLICATE_API_TOKEN` is available, run:

   ```bash
   REPLICATE_API_TOKEN=... node scripts/generate-demo-video.mjs
   ```

   Prompts are in `video-script-bags-v1.md` §AI VIDEO GENERATION PROMPTS. Save outputs as `ai-shot1-feed.mp4` and `ai-shot9-outro.mp4` inside `demo-video/`.

   If no token and Veo/Sora isn't accessible: skip Shot 1 (use a normalized `section1-intro.mp4` retinted), and for Shot 9 reuse `globe-broll.mp4` with a drawtext wordmark overlay (commands below).

5. **Ping back** — once raws are in `demo-video/`, reopen ZERA-500 with a comment: "assets in place" + any asset deltas. I'll finish stitch, mix, overlays, export.

---

## Ready-to-run stitch/mix commands (agent side, after raws land)

The final-cut pipeline is now pre-staged as a single script. Once the six raw recordings (and optional `ai-shot1-feed.mp4` / `ai-shot9-outro.mp4`) land in `demo-video/` (or `demo-video/raw-recordings/`), one command renders the final 1080p cut end-to-end:

```bash
cd <repo-root>/demo-video
python3 build-overlay-cards.py --final   # regen overlay PNGs at 1920x1080
./build-final-bags.sh                    # normalize -> concat -> overlay -> mix -> export
```

Output: `monitor-miroshark-bags-FINAL.mp4` (1920×1080, ~2:00, H.264, AAC 192k, ≤12 Mbps).

What `build-final-bags.sh` does, in order:

1. **Normalize** each raw shot to 1920×1080 / 30 fps / H.264 CRF 19 / AAC 48 kHz stereo. Accepts `.mov`, `.mp4`, or `.mkv` from `.` or `raw-recordings/`. Caches per output, so re-runs after a single fix are fast.
2. **Resolve Shots 1 + 9.** If `ai-shot1-feed.mp4` / `ai-shot9-outro.mp4` are present (from a fresh Veo/Sora/Replicate gen), they're used. Otherwise it falls back to `section1-intro.mp4` retinted for Shot 1, and `globe-broll.mp4 + ovl-06-outro.png` overlay for Shot 9. **Note:** this Mac's homebrew ffmpeg 8.0.1 was built without `libfreetype`, so the `drawtext` filter is unavailable — that's why the Shot 9 wordmark fallback is a PNG overlay, not a drawtext filter. Same workaround used for the rough cut.
3. **Concat** per `concat-bags-final.txt`.
4. **Overlay caption cards** (`ovl-01..06.png` at 1920×1080) at the same shot offsets used in the rough cut.
5. **Mix VO + ducked music bed** (VO full, music at -18 dB, 2 s fade-in / 3 s fade-out, music looped to cover the full duration).
6. **Final export** with `-preset slow -crf 19 -maxrate 12M -bufsize 24M`.

Re-stage from scratch if needed:

- Overlay cards: `python3 build-overlay-cards.py --final` (1080p, no watermark) or no flag (720p, with watermark — rough-cut mode).
- Concat order: `concat-bags-final.txt` (editable if shot durations drift in QC).
- Build script: `build-final-bags.sh` (idempotent; cached normalize outputs are reused).

---

## Post-production checklist

- [ ] All raw screen recordings in `demo-video/` (names above).
- [ ] AI Shots 1 + 9 generated (or acceptable fallbacks in place).
- [ ] `monitor-miroshark-bags-FINAL.mp4` exported and under 200MB.
- [ ] Uploaded to YouTube, "Monitor × MiroShark — Bags Hackathon Demo", public.
- [ ] URL written into `SUBMISSION.md` line 66.
- [ ] DoraHacks submission page updated with the video URL (parent [ZERA-499](/ZERA/issues/ZERA-499)).
