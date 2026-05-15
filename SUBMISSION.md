# Bags Hackathon Submission — Monitor the Situation × MiroShark

**BUIDL:** Monitor the Situation
**Team:** Zero Human Labs
**Tracks:** AI, AI Agents, Solana, DeFi, Payments, Claude Skills
**Deadline:** June 1, 2026

---

## One-Liner

**AI Superforecasting for Solana Token Markets.** Hundreds of AI agents simulate public reaction to every Bags.fm token launch — in real time. Navigate the swarm on a graph. Pay per forecast in Solana USDC.

## Lead

**Monitor the Situation** is AI Superforecasting for Solana token markets. When a creator token launches on Bags.fm, our MiroShark swarm simulates hundreds of AI agents debating it across Twitter, Reddit, and Polymarket — producing a narrative-grounded forecast with traceable beliefs. Live Hyperliquid + Bags.fm risk signals ground every simulation in real market data. Every forecast is explainable: click any agent in the Quartz graph view, see the posts it read and the narrative it joined. Pay-per-query via Solana USDC. No subscription. Agents pay agents.

## Problem

Token launches on Bags.fm happen in seconds. A human analyst cannot keep up. Existing agents either scrape signals or run sentiment models — none of them **simulate** how a crowd of different personas would actually debate and trade the token.

## Solution

Monitor combines live market intelligence with agent-based simulation, all served through agent-native payment rails:

1. **Live risk scoring** from Bags.fm pool data, lifetime fees, and price trajectory
2. **MiroShark swarm simulation** — hundreds of LLM-driven personas (momentum traders, whale-trackers, conservative analysts, shillers, contrarians) debate each launch across simulated Twitter, Reddit, and Polymarket, grounded in a Neo4j knowledge graph
3. **Explainable consensus** — every agent's stance, confidence trajectory, and belief updates are rendered as a navigable Quartz graph
4. **Agent-native payments** — each API endpoint is paywalled with x402 USDC micropayments on Solana devnet

## What Makes It Novel

- **Live + simulated intelligence combined** — not just sentiment, but a simulation of how the crowd would react
- **Graph-grounded personas** — each agent has 5 layers of context (graph attributes, relationships, semantic search, related nodes, LLM web research)
- **Cross-platform context** — traders see social sentiment; social agents see market prices; beliefs propagate between platforms
- **Sliding-window round memory** — LLM-compacted summaries of old rounds keep long simulations coherent
- **Explainable output** — Quartz graph view lets users navigate the agent network, see who said what, and why consensus formed
- **Agent-native payments** — x402 on Solana makes each request pay-per-call, enabling autonomous agent-to-agent commerce

## Active Narratives

Every deep-analysis response tags the token with one or two active narratives. The Quartz graph view clusters pages by narrative.

| Narrative | What it covers |
|-----------|----------------|
| AI Agent Tokens | Tokens tied to autonomous/agentic products — "agents earn, agents own." |
| Creator & Celeb Tokens | Streamer / artist / athlete tokens — "own a piece of the person." |
| Meme Season | Classic meme archetypes — "vibes pump, vibes dump." |
| DeFi Summer 2.0 | Perps DEXs, lending, LSTs, restaking on Solana — "yield is back, on-chain." |
| Infra Plays | L2s, RPC providers, data/indexing, MEV tooling — "picks & shovels." |
| Political & Event Tokens | Election, sports, news-cycle tickers — "bet the outcome, not the company." |
| Gaming & Collectible Fungibles | In-game currencies, ticketed tokens — "engagement becomes liquidity." |
| RWA / Tokenized Assets | Bonds, commodities, real-estate wrappers — "TradFi wrapped, on-chain settled." |

## Architecture

```
[Bags.fm API] ─────┐
[Hyperliquid API] ──┤──→ [Monitor Agent] ──→ [Risk Scores]
[Market signals] ───┘            │
                                 ↓
                      [MiroShark Engine]
                      ├── Neo4j Knowledge Graph
                      ├── Graph-Grounded Persona Generator
                      ├── Twitter / Reddit / Polymarket sims
                      ├── Bags.fm Token sim (new)
                      ├── Belief State Tracker
                      └── ReACT Report Agent
                                 ↓
                      [Unified API (x402 USDC Solana)]
                      [Quartz Graph Frontend]
```

## Technical Stack

- **Monitor:** Python + FastAPI, Hyperliquid + Bags.fm API clients, composite risk scoring (4 weighted signals)
- **MiroShark:** Python + FastAPI + Vue.js, Neo4j graph backend, Anthropic Claude for persona simulation
- **x402 Gateway:** Express + @x402/solana for USDC micropayments on Solana devnet
- **Orchestration:** Docker Compose (Monitor + MiroShark + Neo4j + Solana gateway)
- **Visualization:** Quartz (static-site agent network graph)

## Demo

- **Repo:** https://github.com/Zoidberg-eternal/monitor-the-situation-bags
- **Video:** produced (`demo-video/monitor-miroshark-bags-FINAL.mp4`, 1080p, 2:30) — pending YouTube upload to raeli's account, ZERA-500
- **Quartz graph preview:** (static site, generated from simulation runs)

## Why We'll Win

- **Real product, not a toy** — monitors live tokens with proven risk scoring (carried over from Stellar hackathon submission)
- **Agent-native payments** — demonstrates the exact thesis of the Bags grant program
- **Unique swarm intelligence angle** — nobody else is simulating token launches with hundreds of grounded AI personas
- **Production-grade governance** — circuit breakers, budget caps, trust scoring from Agency-OS
- **Explainable AI** — Quartz graph view makes decisions auditable

## Team

Zero Human Labs — building autonomous AI companies where agents run all non-strategic work.

## Links

- **Website:** https://zero-human-labs.com
- **Previous submission:** Stellar hackathon → https://youtu.be/YUqhQFxMNIc
