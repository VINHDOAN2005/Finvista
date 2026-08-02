import { request } from "./client.js";

export function getSystemicNetwork() {
  return request("/api/systemic/network");
}

export function getTopPropagators(n = 10) {
  const params = new URLSearchParams({ n: String(n) });
  return request(`/api/systemic/propagators?${params.toString()}`);
}

export function getTickerSystemicProfile(ticker) {
  return request(`/api/systemic/${ticker.trim().toUpperCase()}`);
}
