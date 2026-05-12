import express from "express";
import {
  createGovernance,
  governanceMiddleware,
  governanceStatus,
} from "./governance.js";
import { createProxyHandler } from "./proxy.js";
import { buildRouteConfig, type RoutePrice } from "./routes.js";
import { verifySolanaPayment } from "./verify.js";

const PORT = parseInt(process.env.PORT || "3403", 10);
const SOLANA_ADDRESS = process.env.SOLANA_ADDRESS || "";
const SOLANA_NETWORK = process.env.SOLANA_NETWORK || "devnet";
const UPSTREAM_URL = process.env.UPSTREAM_URL || "http://localhost:8402";

if (!SOLANA_ADDRESS) {
  console.error("ERROR: Set SOLANA_ADDRESS to your Solana wallet public key");
  process.exit(1);
}

const app = express();
app.use(express.json());

const governance = createGovernance({
  circuitBreaker: { threshold: 3, cooldownMs: 600_000 },
  budget: { dailyLimitUsd: 50 },
  rateLimit: { windowMs: 60_000, maxRequests: 60 },
});

const routes = buildRouteConfig();

// Health check
app.get("/health", (_req, res) => {
  res.json({
    status: "ok",
    gateway: "solana-x402",
    network: `solana:${SOLANA_NETWORK}`,
    upstream: UPSTREAM_URL,
    payTo: SOLANA_ADDRESS,
    governance: governanceStatus(governance),
  });
});

// Governance middleware for /api routes
app.use("/api", governanceMiddleware(governance));

// x402 payment verification middleware for paid routes
app.use("/api", (req, res, next) => {
  const routeKey = `${req.method} ${req.path}`;

  // Find matching route (handle path params)
  let routeConfig: RoutePrice | undefined;
  for (const [pattern, config] of Object.entries(routes)) {
    const [method, path] = pattern.split(" ");
    if (method !== req.method) continue;
    // Convert express-style :param to regex
    const regex = new RegExp("^" + path!.replace(/:[^/]+/g, "[^/]+") + "$");
    if (regex.test(req.path)) {
      routeConfig = config;
      break;
    }
  }

  if (!routeConfig) {
    return next();
  }

  // Check for payment header
  const paymentHeader = req.headers["x-payment-signature"] as string | undefined;
  if (!paymentHeader) {
    res.status(402).json({
      error: "payment_required",
      price: routeConfig.priceUsdc,
      currency: "USDC",
      network: `solana:${SOLANA_NETWORK}`,
      payTo: SOLANA_ADDRESS,
      description: routeConfig.description,
      accepts: [{
        scheme: "exact",
        network: `solana:${SOLANA_NETWORK}`,
        price: `$${routeConfig.priceUsdc}`,
        payTo: SOLANA_ADDRESS,
        currency: "USDC (SPL)",
      }],
    });
    return;
  }

  // Verify payment signature
  const valid = verifySolanaPayment(paymentHeader, routeConfig.priceUsdc, SOLANA_ADDRESS);
  if (!valid) {
    res.status(402).json({
      error: "payment_invalid",
      message: "Invalid or insufficient payment signature",
    });
    return;
  }

  next();
});

// Proxy all API requests to upstream
const proxy = createProxyHandler(UPSTREAM_URL, governance, "solana");

// Market endpoints
app.get("/api/v1/market/risk-scores", proxy);
app.get("/api/v1/market/risk-scores/:asset", proxy);
app.get("/api/v1/market/alerts", proxy);
app.get("/api/v1/market/prices", proxy);
app.get("/api/v1/market/historical", proxy);
app.get("/api/v1/market/consensus", proxy);

// Token endpoints
app.get("/api/v1/tokens/launches", proxy);
app.get("/api/v1/tokens/risk-scores", proxy);
app.get("/api/v1/tokens/risk-scores/:mint", proxy);
app.get("/api/v1/tokens/sentiment", proxy);
app.get("/api/v1/tokens/deep-analysis/:mint", proxy);
app.post("/api/v1/tokens/simulate", proxy);
app.get("/api/v1/tokens/simulate/:simulation_id/status", proxy);
app.get("/api/v1/tokens/simulate/:simulation_id/consensus", proxy);

app.listen(PORT, () => {
  console.log(`\n🔗 Monitor the Situation — Solana x402 Gateway`);
  console.log(`   Port:       ${PORT}`);
  console.log(`   Network:    solana:${SOLANA_NETWORK}`);
  console.log(`   Upstream:   ${UPSTREAM_URL}`);
  console.log(`   Pay-to:     ${SOLANA_ADDRESS}\n`);
});
