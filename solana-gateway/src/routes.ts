export interface RoutePrice {
  priceUsdc: string;
  description: string;
}

export function buildRouteConfig(): Record<string, RoutePrice> {
  return {
    "GET /api/v1/market/risk-scores": {
      priceUsdc: "0.01",
      description: "Composite risk scores for all monitored assets",
    },
    "GET /api/v1/market/risk-scores/:asset": {
      priceUsdc: "0.005",
      description: "Deep-dive risk analysis for a single asset",
    },
    "GET /api/v1/market/alerts": {
      priceUsdc: "0.005",
      description: "Active high-risk alerts",
    },
    "GET /api/v1/market/prices": {
      priceUsdc: "0.002",
      description: "Raw price snapshot",
    },
    "GET /api/v1/market/historical": {
      priceUsdc: "0.05",
      description: "Historical analysis with candle data (1-60 day lookback)",
    },
    "GET /api/v1/market/consensus": {
      priceUsdc: "0.02",
      description: "Swarm consensus risk assessment",
    },
    "GET /api/v1/tokens/launches": {
      priceUsdc: "0.005",
      description: "Recent Bags.fm token launches with risk scores",
    },
    "GET /api/v1/tokens/risk-scores": {
      priceUsdc: "0.01",
      description: "Risk scores for monitored Bags.fm tokens",
    },
    "GET /api/v1/tokens/risk-scores/:mint": {
      priceUsdc: "0.005",
      description: "Single token risk score by mint address",
    },
    "GET /api/v1/tokens/sentiment": {
      priceUsdc: "0.02",
      description: "Swarm consensus sentiment for a token",
    },
    "GET /api/v1/tokens/deep-analysis/:mint": {
      priceUsdc: "0.05",
      description: "Combined live risk + MiroShark simulation intelligence",
    },
    "POST /api/v1/tokens/simulate": {
      priceUsdc: "0.03",
      description: "Trigger MiroShark social simulation for a token",
    },
    "GET /api/v1/tokens/simulate/:simulation_id/consensus": {
      priceUsdc: "0.03",
      description: "MiroShark simulation consensus results",
    },
    "GET /api/v1/tokens/simulate/:simulation_id/status": {
      priceUsdc: "0.00",
      description: "MiroShark simulation status (free)",
    },
  };
}
