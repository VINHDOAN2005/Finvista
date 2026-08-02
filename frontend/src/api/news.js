import { request } from "./client.js";

export function getNewsImpact(ticker, days = 90, fullPipeline = false) {
  const params = new URLSearchParams({ days: String(days) });
  if (fullPipeline) params.set("full_pipeline", "true");
  return request(`/api/news-impact/${ticker.trim().toUpperCase()}?${params.toString()}`);
}

export function getNewsMLSignal(ticker) {
  return request(`/api/news-impact/${ticker.trim().toUpperCase()}/ml-signal`);
}

export function getNewsSentiment(ticker, days = 30) {
  const params = new URLSearchParams({ days: String(days) });
  return request(`/api/news-impact/${ticker.trim().toUpperCase()}/sentiment?${params.toString()}`);
}

export function runNewsPipeline(ticker, eventDate = null, keyword = null, trainML = false) {
  const params = new URLSearchParams();
  if (eventDate) params.set("event_date", eventDate);
  if (keyword) params.set("keyword", keyword);
  if (trainML) params.set("train_ml", "true");
  const suffix = params.toString() ? `?${params.toString()}` : "";
  return request(`/api/news-impact/${ticker.trim().toUpperCase()}/pipeline${suffix}`);
}
