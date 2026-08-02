# 03. SYSTEM ARCHITECTURE BIBLE
**System:** FINVISTA
**Goal:** Define absolute structural boundaries, data flow, and module responsibilities.

## 1. Top-Level Directory Topology
The repository strictly adheres to a domain-driven design structure.

* `src/api/`: REST/WebSocket controllers (FastAPI). Route definitions ONLY.
* `src/core/`: Application-wide configurations, security (JWT), and exception handlers.
* `src/infra/`: External dependencies (PostgreSQL, Redis, DuckDB, message brokers).
* `src/modules/`: The heart of FINVISTA. Isolated business domains.
* `src/scripts/`: Standalone scripts for DB migration, model training, or maintenance. Never imported into `/modules` or `/api`.
* `data/`: Local storage divided into `raw`, `processed`, and `cache`.

## 2. Module Boundaries & Isolation
FINVISTA comprises 5 major domains. Cross-domain communication must happen via the `Service` layer, NEVER by importing internal implementations.

### 2.1. `cw_pricing` (Covered Warrants)
* **Responsibility:** Theoretical pricing, Greeks calculation, and IV tracking.
* **Engine:** `pricing_core.py` (Analytical Black-Scholes) is the source of truth. `pricing_core_enhanced.py` incorporates ML adjustments (e.g., GA-WOA optimized parameters).
* **Data Flow:** Consumes market data -> Outputs pricing matrices -> Consumed by `trading_engine`.

### 2.2. `regime_analysis`
* **Responsibility:** Market state detection (Bull, Bear, Sideways, Volatility spikes).
* **Engine:** GARCH models for volatility, Hidden Markov Models (HMM) for states.
* **Constraint:** Must output normalized state vectors (e.g., $[0, 1]$ probability arrays) for the AI Committee to digest.

### 2.3. `news_impact`
* **Responsibility:** RAG pipelines on financial reports, sentiment analysis on news.
* **Constraint:** Event-driven. Pipeline execution is strictly sequential: `prepare` $\rightarrow$ `align` $\rightarrow$ `calculate` $\rightarrow$ `test` $\rightarrow$ `report`.

### 2.4. `trading_engine`
* **Responsibility:** Paper trading, portfolio management, and signal execution.
* **AI Committee:** The central decision-maker. It ingests arrays from `cw_pricing`, `regime_analysis`, and `news_impact`.
* **Constraint:** Cannot generate its own pricing logic. Must record transaction fees in all paper trading logs.

### 2.5. `credit_risk`
* **Responsibility:** Financial distress evaluation (PCA, Cluster Analysis) and systemic risk.
* **Constraint:** Operates asynchronously (daily/weekly batch processing), unlike the high-frequency nature of `cw_pricing`.

## 3. Storage Architecture

### Current (Dev — 26/06/2026)
* **SQLite:** Default via `data/finvista.db` — `DATABASE_URL` env overrides to PostgreSQL
* **JSON file cache:** `src/infra/market_cache.py` → `data/processed/market_data_snapshot.json`
* **In-memory dict caches:** NewsImpactService, SystemicRiskService (TTL 30 min)

### Target (Production — Phase 6+)
* **PostgreSQL:** Relational data, user accounts, paper trading ledgers, portfolio states. (Convention: Base object is `Fund`, not `Funds`).
* **DuckDB:** High-performance OLAP queries on processed market tick data.
* **Redis:** Pub/Sub for real-time WebSocket feeds and caching expensive ML inference results. See `backend/04_Redis_Convention.md`.

---

## 4. AI Committee Data Flow (4 Layers)

```
Layer 1: CW Pricing signals     ← cw_pricing/service.py (score, Greeks, IV/HV)
Layer 2: Regime Analysis        ← regime_analysis (HMM bias, GARCH vol)
Layer 3: News Impact            ← news_impact/service.py (ML signal + sentiment) ✅
Layer 4: Gemini Vision          ← ai_client.py (chart pattern skeptic)
         ↓
    Consensus → paper_trader.py
```

**File:** `src/modules/trading_engine/ai_committee_service.py`

---

## 5. Frontend Gap (Phase 5 — Critical)

Backend exposes ~25 REST endpoints + WebSocket.  
**No frontend exists.** Swagger `/docs` is the only UI.

Priority: Next.js SaaS dashboard — see `frontend/01_Frontend_Bible.md`.

---

## 6. Known Architecture Debt

| Issue | Priority | Fix |
|-------|----------|-----|
| KalmanFilter class missing | P0 | `regime_analysis/indicators/kalman_filter.py` |
| discrete_dividends not integrated | P0 | `cw_pricing/models/` |
| No Redis (JSON cache only) | Phase 6 | `infra/redis_client.py` |
| APScheduler (not Celery) | P3 | `api/scheduler.py` |
| news_impact steps flat (no etl/) | P4 | cosmetic refactor |
| No CI/CD pipeline | Phase 8 | `.github/workflows/` |