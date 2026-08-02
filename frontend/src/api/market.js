import { request } from "./client.js";

export function getUnderlyingMarket({ forceRefresh = false, newsLimit = 20, language = "en" } = {}) {
  const params = new URLSearchParams({
    news_limit: String(newsLimit),
    language
  });
  if (forceRefresh) params.set("force_refresh", "true");
  return request(`/api/market/underlyings?${params.toString()}`);
}
