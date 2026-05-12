#!/usr/bin/env python3
"""Regenerate the Bags VO at slower speed so it spans into the outro."""
import json
import os
import sys
import urllib.request

SCRIPT = """A new token just launched on Bags dot F M. Thirty seconds later it's up four hundred percent. Thirty seconds after that, it's rugged. Humans can't keep up — but an A I swarm can.

Meet Monitor the Situation — an autonomous agent watching the entire Bags dot F M firehose, live. Four signals: pool liquidity, lifetime fees, price trajectory, and launch velocity. When the composite risk score crosses threshold, Monitor doesn't just alert — it triggers a deep analysis.

Monitor fires the token into MiroShark — a multi-agent swarm grounded in a Neo Four J knowledge graph. Hundreds of L L M personas — momentum traders, whale-trackers, contrarians, shillers, and conservative analysts — debate the launch across simulated Twitter, Reddit, Polymarket, and Bags dot F M itself. Each persona has five layers of context: graph attributes, relationships, semantic search, related nodes, and live web research. Beliefs propagate across platforms. Rounds compact into summaries so long simulations stay coherent.

Every stance, every confidence update, every debate — rendered as a navigable Quartz graph. You can trace exactly why the swarm converged: which persona moved first, who followed, which arguments flipped the room. Explainable A I, not a black box.

And the whole thing is paywalled — not with A P I keys, but with agent-native payments. Every endpoint speaks x four oh two, the H T T P payment protocol. Hit it unpaid — four oh two. Sign a U S D C micropayment on Solana devnet — two hundred, full analysis J S O N. Autonomous agents can pay each other, per request, on-chain.

Monitor the Situation. MiroShark swarm intelligence. Agent-native payments. All on Solana. Built by Zero Human Labs — where every employee is an A I agent."""

API_KEY = os.environ["OPENAI_API_KEY"]
SPEED = float(sys.argv[1]) if len(sys.argv) > 1 else 0.82
OUT = sys.argv[2] if len(sys.argv) > 2 else "voiceover-bags-v2.mp3"

req = urllib.request.Request(
    "https://api.openai.com/v1/audio/speech",
    data=json.dumps({
        "model": "tts-1-hd",
        "voice": "onyx",
        "input": SCRIPT,
        "speed": SPEED,
        "response_format": "mp3",
    }).encode(),
    headers={
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    },
)
print(f"requesting tts-1-hd onyx, speed={SPEED}, words={len(SCRIPT.split())} …", flush=True)
with urllib.request.urlopen(req) as resp, open(OUT, "wb") as f:
    f.write(resp.read())
sz = os.path.getsize(OUT)
print(f"wrote {OUT}  ({sz/1024:.1f} KB)")
