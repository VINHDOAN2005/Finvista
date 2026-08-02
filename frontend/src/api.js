// Compatibility surface for existing imports while endpoints live by domain.
export { API_BASE_URL, request, setAuthTokenProvider } from "./api/client.js";
export { getAdminSecretStatus } from "./api/admin.js";
export { getCreditHealth, getHealth, getMarketMetadata } from "./api/system.js";
export { getUnderlyingMarket } from "./api/market.js";
export {
  getOpportunities,
  getWarrantHistory,
  getWarrantSimulation,
  refreshMarketScan,
  calculateGreeks
} from "./api/warrants.js";
export {
  getPortfolio,
  placeOrder,
  resetPortfolio,
  scanPortfolio
} from "./api/portfolio.js";
export {
  getMarketRegime,
  getTickerRegime,
  getTickerIndicators
} from "./api/regime.js";
export {
  getSystemicNetwork,
  getTopPropagators,
  getTickerSystemicProfile
} from "./api/systemic.js";
export {
  getNewsImpact,
  getNewsMLSignal,
  getNewsSentiment,
  runNewsPipeline
} from "./api/news.js";
export {
  chatCompletion,
  generateFinancialCommentary
} from "./api/chat.js";
