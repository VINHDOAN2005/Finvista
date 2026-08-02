# EXECUTION ROADMAP — Phase 4.5 → Phase 8
**Status:** ACTIVE  
**Updated:** 26/06/2026  
**Rule:** Complete all Acceptance Criteria + passing tests before moving to next task.

---

## CURRENT STATE SUMMARY

| Layer | Status |
|-------|--------|
| Backend FastAPI (7 routers, ~25 endpoints) | ✅ Production-ready |
| AI Committee 4-layer | ✅ Integrated |
| news_impact (service + 4 routes + Layer 3) | ✅ Complete |
| regime routes | ✅ Exist — KalmanFilter P0 bug |
| Frontend Next.js | ❌ **#1 Priority gap** |
| Redis | ❌ Planned Phase 6 |
| PostgreSQL production | ❌ SQLite default |
| Tests | ⚠️ 1 file only (target: 15+) |
| CI/CD + Docker | ❌ Phase 8 |

---

# SECTION A: BACKEND FIXES (Phase 4.5)

Do BEFORE or IN PARALLEL with Phase 5 frontend.

---

## P0-1: Fix KalmanFilter (BLOCKER)

**Objective:** Make `/api/regime/{ticker}/indicators` return valid `kalman_trend`.

**Files:**
- `src/modules/regime_analysis/indicators/kalman_filter.py` — ADD `KalmanFilter` class
- `tests/test_kalman_filter.py` — CREATE

**Implementation:**
1. Keep `KalmanFilterPrice` as low-level 1D filter
2. Add `KalmanFilter.estimate(ticker, days)` — fetch prices, apply filter, return trend signal
3. Reuse price fetcher pattern from `multi_tf_ema.py`

**Acceptance Criteria:**
- [ ] `GET /api/regime/VNM/indicators` → `kalman_trend.signal` in `BULLISH|BEARISH|NEUTRAL`
- [ ] No `"error"` key in kalman_trend for valid VN30 ticker
- [ ] `pytest tests/test_kalman_filter.py -v` passes

**Effort:** 2-3 hours

---

## P0-2: discrete_dividends Integration Decision

**Objective:** Resolve orphaned `discrete_dividends.py`.

**Files:**
- `src/modules/cw_pricing/models/discrete_dividends.py`
- `src/modules/cw_pricing/models/pricing_core_enhanced.py`

**Option A (implement):** Add `use_discrete_dividends: bool` flag; call `calculate_dividend_adjusted_spot()` before BSM when True.

**Option B (defer):** Add docstring explaining deferral; create GitHub issue reference.

**Acceptance Criteria:**
- [ ] Decision documented in code
- [ ] If Option A: integration test shows price diff for dividend-paying underlying
- [ ] `/api/warrants/opportunities` schema unchanged

**Effort:** 2-4 hours (Option A) | 30 min (Option B)

---

## P1-1: Credit Health Cache

**Objective:** Cache `get_credit_health()` results, TTL 30 minutes.

**Files:**
- `src/modules/credit_risk/service.py`

**Pattern:** Copy from `NewsImpactService._cache` (lines 19-27 in `news_impact/service.py`).

**Acceptance Criteria:**
- [ ] Second request same ticker within 30 min does not query DB
- [ ] Response schema identical
- [ ] Cache invalidated after TTL expires

**Effort:** 1 hour

---

## P1-2: Credit Risk Batch Scan

**Objective:** `GET /api/credit-risk/scan?tickers=VNM,FPT&limit=50`

**Files:**
- `src/api/routes/credit.py` — ADD route
- `src/modules/credit_risk/service.py` — ADD `scan_tickers()`

**Acceptance Criteria:**
- [ ] Returns list of credit health summaries
- [ ] Max 50 tickers enforced (422 if exceeded)
- [ ] Rate limit 10/minute
- [ ] Uses P1-1 cache per ticker

**Effort:** 2 hours

---

## P1-3: AI Analyst Prompt + API

**Objective:** End-user CW analysis prompt with auto data injection.

**Files TO CREATE:**
- `src/modules/cw_pricing/prompts/analyst_prompt.py` — template string
- `src/api/routes/analyst.py` — route
- `src/api/main.py` — mount router

**Template must include (see `Analyst_Prompt.md`):**
- Bước 0: IV/HV pre-check (mandatory)
- Bước 1: Hard filters (Delta ≥ 0.3, Maturity > 45d, Spread < 15%)
- Bước 2: Two-factor analysis (Technical + Fundamental + GEX)
- Bước 3: Verdict + Entry/SL/TP + Theta decay %

**API:**
```
GET /api/analyst-prompt/{ticker}
GET /api/analyst-prompt/{ticker}?cw_symbol=CWXYZ123
```

**Acceptance Criteria:**
- [ ] Response contains filled prompt with real IV, HV, Delta, Theta, Spread, GEX
- [ ] Prompt includes all 4 steps (0-3)
- [ ] Mounted in main.py, visible in /docs

**Effort:** 3 hours

---

## P2: Test Suite (Target 15+ tests)

**Files TO CREATE:**

| File | Tests |
|------|-------|
| `tests/conftest.py` | FastAPI TestClient, mock DB |
| `tests/test_pricing_core.py` | BSM price, Greeks, IV solver, T→0 edge |
| `tests/test_paper_trader.py` | Entry/exit, fee deduction |
| `tests/test_credit_health.py` | 404, cache, pd_score bounds |
| `tests/test_news_impact.py` | get_ml_signal, sentiment |
| `tests/test_regime_routes.py` | 3 regime endpoints |
| `tests/test_kalman_filter.py` | P0 fix validation |
| `tests/test_api_auth.py` | register, login, me |

**Acceptance Criteria:**
- [ ] `pytest tests/ -v` → 15+ passed
- [ ] No live API calls in tests
- [ ] BSM test uses textbook reference value (S=100, K=100, T=1, r=0.05, σ=0.2 → C≈10.4506)

**Effort:** 4-6 hours

---

## P3: Parallel Improvements (Non-blocking)

| Task | File | Effort |
|------|------|--------|
| APScheduler → Celery Beat | `scheduler.py` | 1 day |
| pytest-asyncio setup | `tests/conftest.py` | 0.5 day |
| OpenAPI `/api/v2/` prefix | `main.py` | 1 day |
| Sentry integration | `main.py` | 0.5 day |
| news_impact step files → etl/ | cosmetic refactor | 2 hours |

---

# SECTION B: PHASE 5 — NEXT.JS FRONTEND (Priority #1)

**Objective:** Transform backend API into demoable, sellable SaaS product.

**Timeline:** Weeks 1-3

---

## Sprint 5.1: Foundation (3-4 days)

```bash
npx create-next-app@latest frontend --typescript --tailwind --app --src-dir
cd frontend && npx shadcn@latest init
npm install @tremor/react echarts echarts-for-react @tanstack/react-query zustand next-themes
```

**Deliverables:**
- [ ] `frontend/` directory with App Router structure
- [ ] Layout: Sidebar (7 nav items) + Header + Dark mode toggle
- [ ] Design tokens: navy/teal/amber financial dark theme
- [ ] `lib/api.ts` typed fetch wrapper
- [ ] `lib/types.ts` matching FastAPI schemas
- [ ] Routes scaffolded: `/dashboard`, `/warrants`, `/credit`, `/regime`, `/portfolio`, `/news`
- [ ] `.env.local`: `NEXT_PUBLIC_API_URL=http://localhost:8008`

**Acceptance Criteria:**
- [ ] `npm run dev` → localhost:3000 renders layout
- [ ] Dark mode toggles correctly
- [ ] API client can fetch `/api/regime/market` and display JSON

---

## Sprint 5.2: Warrant Dashboard (4-5 days) ⭐ CORE SCREEN

**Page:** `/warrants`

**Desktop table columns:**
`| Mã CW | CPCS | TCPH | Thị giá | +/-% | IV/HV | Delta | Theta | Score | Tín hiệu |`

**Features:**
- [ ] Data from `GET /api/warrants/opportunities`
- [ ] Sortable columns
- [ ] IV/HV color: >1.3 red, <0.9 green
- [ ] Signal badges: BUY/HOLD/AVOID
- [ ] Sparkline 7 sessions (Tremor inline chart)
- [ ] Filter panel: CPCS/TCPH dropdown, Delta slider, Score slider, Strategy preset
- [ ] Virtual scroll or pagination (216 CW symbols)
- [ ] Loading skeletons

**Mobile (< md):** Card view with `block md:hidden`

**Detail page `/warrants/[symbol]`:**
- [ ] Full Greeks table
- [ ] IV vs HV timeline (ECharts, 90 days)
- [ ] "Copy Analyst Prompt" button → `/api/analyst-prompt/{ticker}`
- [ ] VIP: P/L 2D Heatmap from `/api/warrants/{symbol}/simulate`

**Acceptance Criteria:**
- [ ] Table renders live data from backend
- [ ] Mobile responsive verified at 375px width
- [ ] Filter reduces visible rows correctly

---

## Sprint 5.3: Credit, Regime, Portfolio (3-4 days)

**`/credit`:** Table + PD score + click → systemic exposure  
**`/regime`:** Market badge + GARCH chart + ticker search  
**`/portfolio`:** Equity curve + positions + scan/reset actions

**Acceptance Criteria:**
- [ ] All 3 pages fetch real API data
- [ ] Error states show toast, not blank screen

---

## Sprint 5.4: WebSocket Live (2 days)

- [ ] `hooks/useWebSocket.ts` → `ws://localhost:8008/api/ws`
- [ ] Live CW price/Greeks update without page reload
- [ ] Toast on new AI Committee signal
- [ ] Connection status indicator in Header

---

# SECTION C: PHASE 6 — INFRASTRUCTURE

**Timeline:** Weeks 4-5

---

## 6.1: Redis (2 days)

See `backend/04_Redis_Convention.md` for full spec.

- [ ] `src/infra/redis_client.py` with graceful fallback
- [ ] `redis>=5.0` in requirements.txt
- [ ] Migrate market_cache, credit health, news sentiment caches
- [ ] `GET /health` includes Redis status

---

## 6.2: PostgreSQL (2 days)

- [ ] `DATABASE_URL=postgresql://...` in `.env`
- [ ] Fix `connect_args` for non-SQLite in `database.py`
- [ ] `alembic upgrade head` on PostgreSQL
- [ ] `scripts/maintenance/migrate_sqlite_to_postgres.py`
- [ ] All pytest pass on PostgreSQL

---

## 6.3: Vietcap Real-time Feed (3 days)

- [ ] `src/infra/vietcap_scraper.py` — async WebSocket
- [ ] Push to Redis `cw:live_price:{symbol}` every 15s (9:15-14:45)
- [ ] Fallback to orderbook_scraper if disconnect

---

# SECTION D: PHASE 7 — SAAS MONETIZATION

**Timeline:** Weeks 6-7

---

## 7.1: Auth (3 days)

- [ ] NextAuth.js (Google OAuth + Magic Link)
- [ ] Token exchange → Finvista JWT
- [ ] Route protection middleware

## 7.2: Subscription Tiers (3 days)

| Feature | Free | VIP (150-350k VND/mo) |
|---------|------|----------------------|
| CW table | 5min delay | Real-time |
| Recommendations | Top 5 | Unlimited |
| Greeks | Δ, Γ | Full + Θ, ν, ρ |
| P/L Heatmap | ❌ | ✅ |
| AI Committee | ❌ | ✅ |

- [ ] `subscriptions` DB table
- [ ] `require_vip()` dependency

## 7.3: PayOS Payment (3 days)

- [ ] QR payment flow
- [ ] Webhook → auto upgrade

## 7.4: Zalo OA Alerts (2 days)

- [ ] `src/infra/zalo_alerts.py`
- [ ] Unified notification hub (Telegram + Zalo)

---

# SECTION E: PHASE 8 — DEPLOY & GO-LIVE

**Timeline:** Week 8

---

## 8.1: Docker Compose

```yaml
services: backend, frontend, db (postgres:15), cache (redis:7), worker (celery)
```

- [ ] Multi-stage Dockerfile (python:3.11-slim)
- [ ] Non-root user `finvista_user`
- [ ] `docker-compose.yml` (dev) + `docker-compose.prod.yml`

## 8.2: CI/CD

- [ ] `.github/workflows/ci.yml` — ruff, pytest, docker build
- [ ] `.github/workflows/deploy.yml` — SSH deploy on main merge

## 8.3: Production Deploy

```
Cloudflare → Vercel (frontend) + VPS (backend/nginx/postgres/redis)
Domain: finvista.vn
SSL: Let's Encrypt certbot
```

## 8.4: Load Testing + Beta

- [ ] Locust: 5000 users, 100 rps on `/api/warrants/opportunities`
- [ ] p95 latency < 500ms
- [ ] Beta invite: 100 users

---

# TIMELINE

```
Week 0:   P0-1 KalmanFilter + P1-1 credit cache
Week 1:   Phase 5.1 + 5.2 (Next.js + Warrant Dashboard)
Week 2:   Phase 5.3 + 5.4 (Credit/Regime/Portfolio + WebSocket)
Week 3:   Phase 5.2 polish (Mobile, P/L Heatmap, UX)
Week 4:   Phase 6.1 + 6.2 (Redis + PostgreSQL)
Week 5:   Phase 6.3 + P2 tests
Week 6:   Phase 7.1 + 7.2 (Auth + Subscriptions)
Week 7:   Phase 7.3 + 7.4 (PayOS + Zalo)
Week 8:   Phase 8 (Docker, CI/CD, Deploy, Beta)
```

---

# START NOW — 3 IMMEDIATE ACTIONS

```bash
# 1. Fix P0 KalmanFilter (backend, 30 min)
# Edit: src/modules/regime_analysis/indicators/kalman_filter.py

# 2. Create frontend (15 min)
npx create-next-app@latest frontend --typescript --tailwind --app --src-dir

# 3. First warrants page (2 hours)
# frontend/src/app/warrants/page.tsx
# Fetch GET http://localhost:8008/api/warrants/opportunities
```

---

# DEFINITION OF DONE (All Tasks)

1. ✅ Code merged, no linter errors
2. ✅ Tests pass (`pytest tests/ -v`)
3. ✅ API schema unchanged (unless task explicitly changes it)
4. ✅ Smoke test 5 core endpoints after change
5. ✅ Relevant Bible file conventions followed
