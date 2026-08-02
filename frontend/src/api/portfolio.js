import { request } from "./client.js";

export function getPortfolio() {
  return request("/api/portfolio");
}

export function placeOrder({ symbol, side, qty, price, reason }) {
  return request("/api/portfolio/orders", {
    method: "POST",
    body: JSON.stringify({
      symbol: symbol.trim().toUpperCase(),
      side: side.toUpperCase(),
      qty,
      price,
      reason
    })
  });
}

export function resetPortfolio() {
  return request("/api/portfolio/reset", { method: "POST" });
}

export function scanPortfolio(force = false) {
  const params = new URLSearchParams({ force: String(force) });
  return request(`/api/portfolio/scan?${params.toString()}`, { method: "POST" });
}
