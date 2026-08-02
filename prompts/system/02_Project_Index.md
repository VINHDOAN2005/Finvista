# 02. PROJECT FILE INDEX & API MAP
**Purpose:** Quick lookup for AI agents — where things live and how they connect.

---

## 1. Entry Points

| File | Role |
|------|------|
| `run.py` | Start FastAPI server (uvicorn) |
| `src/api/main.py` | App factory, router mounting, CORS, startup |
| `src/api/scheduler.py` | APScheduler periodic jobs |
| `src/core/config.py` | Environment config, paths, constants |
| `src/core/database.py` | SQLAlchemy engine, models, SessionLocal |
| `alembic/env.py` | Alembic migration env |

---

## 2. API Layer (`src/api/`)

| File | Endpoints |
|------|-----------|
| `routes/auth.py` | `POST /register`, `POST /login`, `GET /me` |
| `routes/warrants.py` | `/api/warrants/opportunities`, `/greeks`, `/scan`, `/{symbol}/simulate`, `/history`, `/deep-analysis` |
| `routes/portfolio.py` | `GET/POST /api/portfolio`, `/orders`, `/reset`, `/scan` |
| `routes/credit.py` | `/api/credit-health/{ticker}`, `/api/systemic/*` |
| `routes/regime.py` | `/api/regime/market`, `/api/regime/{ticker}`, `/indicators` |
| `routes/news_impact.py` | `/api/news-impact/{ticker}`, `/ml-signal`, `/sentiment`, `/pipeline` |
| `routes/chat.py` | `POST /`, `/financial-commentary`, `/trading-signal-commentary` |
| `dependencies.py` | JWT auth, rate limiter, DB session deps |
| `state.py` | Loaded ML models at startup |
| `websocket.py` | WebSocket handler |

---

## 3. Infrastructure (`src/infra/`)

| File | Role |
|------|------|
| `market_cache.py` | Session-aware JSON cache for CW market data |
| `telegram_alerts.py` | Telegram HTML push → `configs/telegram_config.json` |
| `telegram_hub.py` | Unified alert dispatcher |
| `telegram_webhook.py` | Telegram webhook handler |
| `ai_client.py` | Gemini / LLM client wrapper |
| `chart_generator.py` | Chart generation for reports |
| `news_alerts.py` | News alert pipeline |
| `orderbook_scraper.py` | Orderbook data (Vietstock/SSI) |
| `trade_scraper.py` | Trade data scraper |
| `redis_client.py` | **TO CREATE** — Phase 6 |

---

## 4. Domain Modules

### 4.1 `src/modules/cw_pricing/`

| Path | Role |
|------|------|
| `service.py` | Main pricing orchestration (~20KB) |
| `models/pricing_core.py` | Black-Scholes baseline — **SOURCE OF TRUTH** |
| `models/pricing_core_enhanced.py` | GA-WOA / ML enhancement layer |
| `models/discrete_dividends.py` | Discrete cash dividend adjustment (**not yet integrated**) |
| `models/gex_engine.py` | Gamma exposure engine |
| `models/sabr_vol_surface.py` | SABR volatility surface |
| `backtest/` | 13 files — backtester, ranker, performance_evaluator, … |
| `etl/` | CW data extraction from SSI |

### 4.2 `src/modules/credit_risk/`

| Path | Role |
|------|------|
| `service.py` | `get_credit_health(ticker)` — XGBoost inference |
| `models/merton_engine.py` | Merton structural model |
| `models/credit_pipeline.py` | Full ML pipeline |
| `models/credit_step1..8` | Pipeline steps |
| `systemic/systemic_service.py` | Contagion network (30min cache) |
| `systemic/network_builder.py` | NetworkX graph builder |
| `etl/merton_data_ingestor.py` | Daily Merton solver → DB |

### 4.3 `src/modules/regime_analysis/`

| Path | Role |
|------|------|
| `service.py` | Regime orchestration |
| `indicators/hmm_regime.py` | HMM 4-state VNINDEX model |
| `indicators/garch_volatility_forecaster.py` | GARCH(1,1) forecast |
| `indicators/garch_evt_var.py` | GARCH + EVT VaR |
| `indicators/kalman_filter.py` | `KalmanFilterPrice` only — **missing `KalmanFilter` wrapper (P0 bug)** |
| `indicators/regime_detector.py` | RegimeDetector |
| `indicators/multi_tf_ema.py` | Multi-timeframe EMA |
| `indicators/volatility_models.py` | Realized vol |

### 4.4 `src/modules/news_impact/`

| Path | Role |
|------|------|
| `service.py` | Public API + ML model load + 30min cache |
| `pipeline.py` | Dual-layer pipeline orchestrator |
| `forecast_engine.py` | Forecast logic |
| `exposure_assessor.py` | Exposure assessment |
| `reality_checker.py` | Reality check layer |
| `news_step1..9` | Pipeline steps (flat — refactor to etl/ later) |
| Model: `data/processed/news_ml_model.joblib` | Trained ML model |

### 4.5 `src/modules/trading_engine/`

| Path | Role |
|------|------|
| `orchestrator.py` | Main trading loop — uses `asyncio.run()` ✅ |
| `ai_committee_service.py` | 4-layer AI decision (Gemini) |
| `paper_trader.py` | Paper trading execution |
| Layer 3 integration | Lines 232-233: NewsImpactService ML + sentiment |

---

## 5. Config Files (`configs/`)

| File | Purpose |
|------|---------|
| `telegram_config.json` | Bot token, chat IDs |
| `telegram_hub_state.json` | Hub state persistence |
| `sector_mapping.json` | Sector → ticker mapping |
| `macro_indicators.json` | Macro indicator definitions |
| `opt_cw_params.json` | Optimized CW parameters |
| `paper_portfolio.json` | Paper portfolio config |
| `underlying_hv_cache.json` | HV cache per underlying |

---

## 6. Data Directories

```
data/
├── finvista.db              ← SQLite (default)
├── raw/                     ← scraped raw data
├── processed/               ← ML models, processed CSVs/JSONs
│   ├── news_ml_model.joblib
│   └── market_data_snapshot.json  ← JSON cache (via market_cache.py)
└── cache/                   ← misc cache
```

---

## 7. Scripts (`scripts/`)

| Directory | Examples |
|-----------|----------|
| `model_training/` | `train_ml_regime.py`, `calibrate_merton.py`, `market_merton_scan.py` |
| `trading/` | `stress_test_portfolio.py`, `batch_generate_reports.py`, `run_telegram_polling.py` |
| `maintenance/` | `e2e_validation.py`, `health_check_connectivity.py`, `gemini_web2api.py` |
| `data_pipelines/` | `backfill_ml_data.py`, `market_gex_report.py` |

**Rule:** Never import scripts from `src/modules/` or `src/api/`.

---

## 8. Tests (`tests/`)

| File | Coverage |
|------|----------|
| `test_regime_portfolio.py` | Regime + portfolio integration |

**TO CREATE (target 15+ tests):**
- `test_pricing_core.py`
- `test_paper_trader.py`
- `test_credit_health.py`
- `test_news_impact.py`
- `test_regime_routes.py`
- `test_kalman_filter.py`
- `test_api_auth.py`
- `conftest.py`

---

## 9. Key Integration Points

```
Market Data (scrapers)
    ↓
market_cache.py (JSON) → cw_pricing/service.py
    ↓
/api/warrants/opportunities
    ↓
trading_engine/orchestrator.py
    ↓
ai_committee_service.py
    ├── Layer 1: cw_pricing signals
    ├── Layer 2: regime_analysis
    ├── Layer 3: news_impact (ML + sentiment)  ← line 232-233
    └── Layer 4: Gemini Vision
    ↓
paper_trader.py → PostgreSQL/SQLite portfolio
    ↓
telegram_alerts.py → push notification
```

---

## 10. Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | `sqlite:///data/finvista.db` | DB connection |
| `REDIS_URL` | — | **Phase 6** — `redis://localhost:6379/0` |
| `GEMINI_API_KEY` | — | AI Committee Layer 4 |
| `JWT_SECRET` | — | Auth token signing |
| `NEXT_PUBLIC_API_URL` | — | **Phase 5** frontend |

Validated via `src/core/config.py` + `pydantic-settings`.
