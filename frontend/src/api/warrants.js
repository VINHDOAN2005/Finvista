import { request } from "./client.js";

export function getOpportunities({
  strategy,
  underlying,
  limit,
  forceRefresh = false,
  vn30Only = false,
  industry = ""
}) {
  const params = new URLSearchParams({
    strategy,
    limit: String(limit || 10)
  });
  if (underlying?.trim()) params.set("underlying", underlying.trim().toUpperCase());
  if (forceRefresh) params.set("force_refresh", "true");
  if (vn30Only) params.set("vn30_only", "true");
  if (industry?.trim()) params.set("industry", industry.trim());
  return request(`/api/warrants/opportunities?${params.toString()}`);
}

export function getWarrantSimulation(symbol) {
  return request(`/api/warrants/${symbol.trim().toUpperCase()}/simulate`);
}

export function getWarrantHistory(symbol, days = 240) {
  return request(`/api/warrants/${symbol.trim().toUpperCase()}/history?days=${days}`);
}

export function refreshMarketScan(strategy = "balanced") {
  const params = new URLSearchParams({ strategy });
  return request(`/api/warrants/scan?${params.toString()}`, { method: "POST" });
}

export function calculateGreeks({
  underlyingPrice,
  strikePrice,
  daysToMaturity,
  impliedVolatility,
  conversionRatio = 1.0,
  riskFreeRate
}) {
  return request("/api/warrants/greeks", {
    method: "POST",
    body: JSON.stringify({
      underlying_price: underlyingPrice,
      strike_price: strikePrice,
      days_to_maturity: daysToMaturity,
      implied_volatility: impliedVolatility,
      conversion_ratio: conversionRatio,
      risk_free_rate: riskFreeRate
    })
  });
}
