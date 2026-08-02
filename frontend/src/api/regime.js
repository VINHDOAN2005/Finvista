import { request } from "./client.js";

export function getMarketRegime() {
  return request("/api/regime/market");
}

export function getTickerRegime(ticker, days = 252) {
  const params = new URLSearchParams({ days: String(days) });
  return request(`/api/regime/${ticker.trim().toUpperCase()}?${params.toString()}`);
}

export function getTickerIndicators(ticker, days = 252) {
  const params = new URLSearchParams({ days: String(days) });
  return request(`/api/regime/${ticker.trim().toUpperCase()}/indicators?${params.toString()}`);
}
