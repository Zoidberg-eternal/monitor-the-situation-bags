# Monitor the Situation

**AI Superforecasting for Solana Token Markets.**
*See the swarm. Trade the edge.*

Hundreds of AI agents simulate public reaction to every [Bags.fm](https://bags.fm) token launch — in real time. Navigate the swarm on a graph. Pay per forecast in Solana USDC.

When a creator token launches on Bags.fm, our MiroShark swarm simulates hundreds of AI agents debating it across Twitter, Reddit, and Polymarket — producing a narrative-grounded forecast with traceable beliefs. Live Hyperliquid + Bags.fm risk signals ground every simulation in real market data. Every forecast is explainable: click any agent in the Quartz graph view, see the posts it read and the narrative it joined. Pay-per-query via Solana USDC. No subscription. Agents pay agents.

> Built for the [Bags Hackathon](https://dorahacks.io/hackathon/the-bags-hackathon/detail) by [Zero Human Labs](https://zero-human-labs.com) · Deadline: June 1, 2026

**[Video Demo](https://youtu.be/YUqhQFxMNIc)** · **[Quartz Graph View](#quartz-graph-view)**

---

## Why This Matters

Token launches on Bags.fm happen in seconds. A human analyst cannot keep up. Existing agents either scrape signals or run sentiment models — none of them **simulate** how a crowd of different personas would actually debate and trade the token.

Monitor does both:

1. **Live risk scoring** from Bags.fm pool data, lifetime fees, and price trajectory
2. **Simulated public reaction** via [MiroShark](https://github.com/aaronjmars/MiroShark) — a swarm of LLM-driven personas (momentum traders, whale-trackers, conservative analysts, shillers, contrarians) debate the launch across simulated Twitter + Reddit + a prediction market. Each simulation runs in <10 min for ~$1 (Cheap preset) to ~$3.50 (Best preset).
3. **Explainable consensus** — every agent's stance, quotes, and belief trajectory are rendered as a navigable [Quartz](https://quartz.jzhao.xyz/) graph
4. **Agent-native payments** — each endpoint is paywalled with x402 USDC micropayments on Solana devnet

---

## Architecture

```
[Bags.fm Public API]              [Hyperliquid DEX]
        |                                |
        v                                v
        +-------- Python Risk Engine ----+
                   (FastAPI :8402)
                        |
         +--------------+---------------+
         |                              |
         v                              v
   [MiroShark API]               [Neo4j Graph DB]
  (swarm simulation)            (entities + edges)
         |                              |
         v                              v
   [Quartz Static Site]          [Export Pipeline]
    (graph view :8080)          (markdown generator)
                        ^
                        |
         +--------------+---------------+
         |                              |
[Solana x402 Gateway]           [Stellar x402 Gateway]
    (Express :3403)                (Express :3402)
         |                              |
         v                              v
  [Solana Devnet USDC]          [Stellar Testnet USDC]
```

**Flow:**
1. Monitor polls Bags.fm every 2 minutes for new launches
2. Each token gets a composite live risk score from pool depth, fee velocity, and trade quote slippage
3. For tokens crossing a sentiment threshold, Monitor fires a MiroShark simulation — a multi-round debate between 8–12 LLM personas on a simulated Twitter + Reddit
4. Consensus (sentiment, stance distribution, notable quotes) is returned and cached
5. The export pipeline dumps the agent network + simulation rounds as Obsidian-style markdown; Quartz renders it as an interactive graph
6. All API reads are paywalled via x402 — Solana devnet is the primary gateway, Stellar is also supported

---

## Quick Start (Docker Compose)

The full stack runs in one command via Docker Compose. It boots Monitor, MiroShark, Neo4j, and the Solana gateway.

```bash
git clone https://github.com/Zoidberg-eternal/monitor-the-situation-bags.git
cd monitor-the-situation-bags

# Configure the 3 required keys in ONE file — the bags .env (compose reads it):
cp .env.example .env
#   BAGS_FM_API_KEY  — from https://dev.bags.fm
#   LLM_API_KEY      — an OpenRouter key (defaults target OpenRouter + mimo)
#   SOLANA_ADDRESS   — a REAL Solana devnet wallet pubkey you control

docker compose up --build
```

> **Heads-up for reviewers:** these 3 keys are secrets and are not committed.
> With them set in the single bags `.env`, all four services come up. Point 4
> (live x402 devnet payment) needs the **real `SOLANA_ADDRESS` you supply** —
> the gateway exits on startup if it is unset or not a valid devnet wallet, so
> a stub will not transact. The demo video shows the configured stack live.

This starts:

| Service | Port | Purpose |
|---------|------|---------|
| `monitor` | 8402 | Risk engine (Python/FastAPI) |
| `solana-gateway` | 3403 | x402 payment gateway (Solana devnet) |
| `miroshark` | 5001, 3000 | Swarm simulation API + web UI |
| `neo4j` | 7474, 7687 | Knowledge graph storage |

### Verify it's running

```bash
curl http://localhost:8402/health
curl http://localhost:3403/health

# Hit a free endpoint — recent Bags.fm token launches
curl http://localhost:8402/api/v1/tokens/launches

# Grab a real mint from the live launch feed
MINT=$(curl -s http://localhost:8402/api/v1/tokens/launches | python3 -c 'import sys,json; print(json.load(sys.stdin)[0]["tokenMint"])')

# Trigger a MiroShark simulation for that token.
# NOTE: `mint` is a QUERY PARAMETER, not a JSON body — copy-paste returns 200.
curl -X POST "http://localhost:8402/api/v1/tokens/simulate?mint=$MINT"

# Combined live risk + MiroShark consensus. Returns 200 immediately; the
# `simulation_consensus` field populates once the sim completes (a few
# minutes). On a fresh empty Neo4j the static demo persona graph is seeded
# automatically on boot, so the simulation runs with no manual step. If a
# graph is unavailable, `simulation_note` explains the degraded state
# instead of returning a silent null.
curl "http://localhost:8402/api/v1/tokens/deep-analysis/$MINT"
```

---

## API Endpoints

All `/api/*` endpoints on the gateway require x402 payment. Endpoints served directly by the risk engine (port 8402) are free for local development; production traffic should go through the gateway.

### Token endpoints (Bags.fm + MiroShark)

| Endpoint | Price (USDC) | Description |
|----------|--------------|-------------|
| `GET /api/v1/tokens/launches` | $0.005 | Recent Bags.fm token launches with live risk scores |
| `GET /api/v1/tokens/risk-scores` | $0.01 | All monitored tokens with composite risk scores |
| `GET /api/v1/tokens/risk-scores/:mint` | $0.005 | Single token, deep dive |
| `GET /api/v1/tokens/sentiment` | $0.02 | Swarm consensus sentiment |
| `GET /api/v1/tokens/deep-analysis/:mint` | $0.05 | Combined live risk + MiroShark consensus |
| `POST /api/v1/tokens/simulate` | $0.03 | Trigger a new MiroShark simulation for a token |
| `GET /api/v1/tokens/simulate/:id/consensus` | $0.03 | Fetch consensus results |
| `GET /api/v1/tokens/simulate/:id/status` | free | Check simulation status |

### Hyperliquid perps endpoints (legacy, still live)

| Endpoint | Price | Description |
|----------|-------|-------------|
| `GET /api/v1/market/risk-scores` | $0.01 | Composite risk for 21 perp/commodity assets |
| `GET /api/v1/market/risk-scores/:asset` | $0.005 | Deep dive on a single asset |
| `GET /api/v1/market/alerts` | $0.005 | Active high-severity alerts |
| `GET /api/v1/market/prices` | $0.002 | Raw price snapshot |
| `GET /api/v1/market/historical` | $0.05+ | Historical analysis (1–60 day lookback) |
| `GET /api/v1/market/consensus` | $0.02 | Swarm consensus risk assessment |

---

## Risk Scoring

### Live token risk (`monitor/token_risk.py`)

Composite score (0–100) computed from Bags.fm pool data:

| Component | Signal |
|-----------|--------|
| Pool depth | USDC reserve size — shallow pools flagged |
| Fee velocity | Lifetime fees vs time-since-launch |
| Slippage | 1% / 5% trade quote spread |
| Age penalty | Very new launches scored higher risk |

### Legacy perp risk (`monitor/risk.py`)

Four-component weighted score for Hyperliquid assets:

| Component | Weight | What it measures |
|-----------|--------|------------------|
| Funding Rate | 30% | Magnitude of hourly funding |
| Volume Spike | 25% | Current vs rolling 12-sample average |
| OI Shift | 25% | Open interest change vs previous snapshot |
| Basis Deviation | 20% | Mark-oracle price spread |

---

## Swarm Simulation (MiroShark)

`monitor/swarm/` wires the swarm into the risk engine:

- `personas.py` — generates a balanced cohort of LLM persona profiles (momentum trader, whale-tracker, conservative analyst, shiller, contrarian, etc.) seeded from token metadata
- `debate.py` — orchestrates multi-round debate: each persona receives others' stances and updates beliefs round-to-round
- `consensus.py` — aggregates final sentiment distribution, belief trajectory, notable quotes

Under the hood, heavy simulation traffic is handed off to the standalone [MiroShark](https://github.com/Zoidberg-eternal/miroshark) service (container at `miroshark:5001`), which also provides a Neo4j-backed knowledge graph.

### Know Your Agent (KYA) — signed attestations

Every forecast returned by `/api/v1/tokens/deep-analysis/{mint}` ships with cryptographic provenance, aligned with a16z's 2026 *Know Your Agent* thesis: agents need verifiable credentials to transact.

- Each simulated agent is minted an **ed25519 keypair** at sim-start. The public key is its stable `did:miroshark:<base58>` identity; the private key never leaves the MiroShark process boundary.
- Every agent action (post/comment/stance update) is signed with that private key and recorded in a `signed_actions.jsonl` sibling log.
- The final consensus includes a per-agent attestation plus a sim-root-signed manifest so the entire forecast is a verifiable chain: `agent DID → signed action → signed consensus → your request`.

Response fields:

```json
{
  "agent_attestations": [
    {"agent_did": "did:miroshark:...", "stance": "bullish", "confidence": 0.72,
     "quote_hash": "sha256:...", "signed_at": "...", "signature": "ed25519:..."}
  ],
  "sim_root_did": "did:miroshark:...",
  "manifest": {...},
  "manifest_signature": "ed25519:..."
}
```

Verify any signature against MiroShark directly — no ed25519 library required:

```bash
curl -X POST http://miroshark:5001/api/verify \
  -H 'Content-Type: application/json' \
  -d '{
    "did": "did:miroshark:2XtDTXuhC7hrsbfU2TYbvRqz5h7Nnw8DDof9d8PyvU6g",
    "payload": {"agent_did": "did:miroshark:...", "stance": "bullish", "...": "..."},
    "signature": "ed25519:..."
  }'
# → {"valid": true, "did_matches_pubkey": true, "algorithm": "ed25519"}
```

Or decode the DID directly: the base58 body *is* the ed25519 public key. `GET /api/agents/<did>/pubkey` exposes that as a convenience.

---

## Quartz Graph View

The export pipeline renders every simulation as an [Obsidian-style](https://obsidian.md) vault, served by [Quartz](https://quartz.jzhao.xyz/) as an interactive graph site. Every agent, token, simulation, and round is a clickable node; wikilinks form the edges.

Live at `quartz-monitor/` in the repo:

```
quartz-monitor/
├── build.sh                     # One-command re-export + rebuild
├── scripts/export-to-quartz.py  # MiroShark sim data → Obsidian markdown
└── quartz-site/
    └── content/
        ├── index.md             # Dashboard
        ├── agents/              # One page per persona
        ├── tokens/              # One page per token + risk score
        ├── simulations/         # One page per sim + sentiment distribution
        └── rounds/              # Round-by-round detail
```

Build and serve locally:

```bash
cd quartz-monitor
./build.sh                       # exports sim data + builds site
# site served at http://localhost:8080
```

142 pages are generated from the current sim data (22 agents, 4 tokens, 4 simulations, ~112 rounds), with force-directed graph view showing agent clusters, stance drift, and token ↔ agent ↔ simulation edges.

---

## Payment Flow (x402 on Solana)

```
Client                        Gateway :3403              Solana Devnet
  |                                |                          |
  |--- GET /api/v1/tokens/... ---->|                          |
  |                                |                          |
  |<-- 402 Payment Required -------|                          |
  |    (price, payTo, network)     |                          |
  |                                |                          |
  |--- Sign + submit tx ---------->|                          |
  |    (PAYMENT-SIGNATURE header)  |                          |
  |                                |--- Verify tx on-chain -->|
  |                                |<-- Confirmed ------------|
  |                                |                          |
  |<-- 200 + deep analysis --------|                          |
```

The Stellar gateway (`stellar-gateway/` on port 3402) follows the same protocol against Stellar testnet USDC, with OpenZeppelin Channels as the facilitator. See `stellar-gateway/README.md` for that path.

---

## Project Structure

```
monitor-the-situation-bags/
├── monitor/                    # Python risk engine + swarm
│   ├── bags_client.py          # Bags.fm public API v2 client
│   ├── miroshark_client.py     # MiroShark bridge client
│   ├── token_risk.py           # Bags token risk scoring
│   ├── swarm/                  # Persona generation, debate, consensus
│   ├── client.py               # Hyperliquid client (legacy perps)
│   ├── risk.py                 # Perp risk scoring (legacy)
│   ├── historical.py           # Historical analysis
│   ├── server.py               # FastAPI server (:8402)
│   └── x402/                   # x402 helpers shared across gateways
├── solana-gateway/             # TypeScript x402 gateway (Solana devnet)
│   └── src/
│       ├── index.ts
│       ├── routes.ts           # Route pricing config
│       ├── verify.ts           # Solana tx verification
│       ├── governance.ts       # Circuit breaker, budget caps, rate limiting
│       └── proxy.ts
├── stellar-gateway/            # TypeScript x402 gateway (Stellar testnet)
├── scripts/
│   └── generate-demo-video.mjs # AI-generated demo video pipeline
├── docker-compose.yml          # Full stack: monitor + miroshark + neo4j + gateway
├── Dockerfile
├── pyproject.toml
├── .env.example
└── README.md
```

---

## Stellar Testnet Proof (legacy hackathon)

The Stellar gateway still works end-to-end against testnet USDC. All transactions verifiable on-chain:

| Transaction | Operation | Explorer |
|-------------|-----------|----------|
| Account creation (Friendbot) | `create_account` | [View](https://stellar.expert/explorer/testnet/op/8627906397908993) |
| USDC trustline | `change_trust` | [View](https://stellar.expert/explorer/testnet/op/8627910692859905) |
| XLM → USDC swap | `path_payment_strict_send` | [View](https://stellar.expert/explorer/testnet/op/8627914987814913) |

- **Payer:** [`GD5XMO...DJUYS`](https://stellar.expert/explorer/testnet/account/GD5XMOUUQBIJDFJ6T4LCS5TWWQJURLVOC5D6ISVHT72DBUUNXNODJUYS)
- **Gateway:** [`GA64KD...476S7`](https://stellar.expert/explorer/testnet/account/GA64KD2Y3ZRZGSIGXOXL7AMNNAWEF7QJUBALIFPRX7IWYYHSMUJ476S7)

Reproduce: `cd stellar-gateway && npm run setup:testnet && npm run demo:e2e`

---

## Tech Stack

- **Risk Engine:** Python 3.11, FastAPI, httpx, hyperliquid-python-sdk
- **Data Sources:** Bags.fm public API v2, Hyperliquid DEX, MiroShark simulation API
- **Swarm Simulation:** MiroShark (LLM personas + Twitter/Reddit simulation)
- **Knowledge Graph:** Neo4j 5 (entities + relationships)
- **Graph View:** Quartz (static site + interactive graph)
- **Payment Gateways:** TypeScript / Express with @x402 middleware
- **Blockchains:** Solana (devnet) primary, Stellar (Soroban) alternate
- **Settlement:** USDC on Solana SPL / Stellar SEP-41

---

## License

MIT

---

Built by [ZERA](https://zero-human-labs.com) for the [Bags Hackathon](https://dorahacks.io/hackathon/the-bags-hackathon/detail).
