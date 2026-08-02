# 02. API CONVENTION & ROUTE DESIGN
**Domain:** `src/api/routes/`  
**Framework:** FastAPI + Pydantic V2 + SlowAPI

---

## 1. Thin Route Principle

FastAPI route functions MUST contain **zero business logic**.

```python
# ✅ CORRECT
@router.get("/api/credit-health/{ticker}")
def get_corporate_credit_health(ticker: str):
    return CreditRiskService.get_credit_health(ticker)

# ❌ WRONG — logic in route
@router.get("/api/credit-health/{ticker}")
def get_corporate_credit_health(ticker: str):
    db = SessionLocal()
    row = db.query(...).filter(...).first()  # REJECT
    pd_score = xgb_model.predict(...)         # REJECT
    return {"score": pd_score}
```

**Allowed in routes:**
- Path/query parameter parsing
- `Query()` validation (ge, le, default, description)
- Dependency injection via `Depends()`
- Delegating to `Service` layer
- HTTPException re-raise from service

---

## 2. URL Naming Convention

| Pattern | Example | Use |
|---------|---------|-----|
| `/api/{resource}` | `/api/warrants/opportunities` | Collection / list |
| `/api/{resource}/{id}` | `/api/credit-health/VNM` | Single entity |
| `/api/{resource}/{id}/{action}` | `/api/news-impact/VNM/ml-signal` | Sub-resource |
| `/api/{domain}/{resource}` | `/api/regime/market` | Domain-scoped |

**Rules:**
- Always lowercase, hyphen-separated paths
- Ticker params: `.upper().strip()` in service layer, not route
- Versioning (future): `/api/v2/warrants/...` — do not break v1

---

## 3. Request Validation

Use FastAPI `Query()` for all optional params:

```python
@router.get("/api/regime/{ticker}")
def get_ticker_regime(
    ticker: str,
    days: int = Query(default=252, ge=60, le=1250, description="Số ngày dữ liệu"),
):
    ...
```

Use Pydantic models for POST body:

```python
class GreekCalculatorRequest(BaseModel):
    symbol: str
    spot: float = Field(gt=0)
    strike: float = Field(gt=0)
    maturity_days: int = Field(ge=1, le=730)
    volatility: float = Field(gt=0, le=5.0)
    risk_free_rate: float = Field(default=0.045, ge=0, le=1.0)
```

---

## 4. Response Format

**Current pattern (mixed — preserve for backward compat):**

Most endpoints return domain-specific dicts directly:
```json
{ "ticker": "VNM", "pd_score": 0.12, "risk_label": "LOW" }
```

**Target pattern for NEW endpoints:**
```json
{
  "status": "ok",
  "data": { ... },
  "meta": { "cached": true, "ttl_seconds": 1800 }
}
```

**Error responses:**
```json
{
  "status": "error",
  "error_code": "TICKER_NOT_FOUND",
  "message": "Ticker 'XYZ' not found in credit health database"
}
```

Use `HTTPException` with appropriate status codes:
- `404` — entity not found
- `422` — validation error (automatic via Pydantic)
- `429` — rate limit exceeded (SlowAPI)
- `500` — unexpected server error (log + generic message to client)

---

## 5. Authentication & Authorization

**Current:** JWT via `src/api/routes/auth.py`

```python
from src.api.dependencies import get_current_user

@router.get("/api/portfolio")
def get_portfolio(current_user=Depends(get_current_user)):
    ...
```

**Phase 7 — Subscription tiers:**
```python
from src.api.dependencies import require_vip

@router.get("/api/warrants/{symbol}/simulate")
def simulate_pl(symbol: str, user=Depends(require_vip)):
    ...
```

**Public endpoints (no auth required):**
- `/api/warrants/opportunities` (free tier: 5min delay)
- `/api/regime/market`
- `/docs`, `/redoc`

---

## 6. Rate Limiting

Configured in `src/api/dependencies.py` via SlowAPI.

```python
from src.api.dependencies import limiter

@router.get("/api/warrants/opportunities")
@limiter.limit("30/minute")
def get_opportunities(request: Request):
    ...
```

**Guidelines:**
- Heavy endpoints (full pipeline, systemic network): `5/minute`
- Standard read endpoints: `30/minute`
- Auth endpoints: `10/minute`

---

## 7. Router Registration

All routers mounted in `src/api/main.py`:

```python
from src.api.routes import auth, chat, credit, news_impact, portfolio, regime, warrants

app.include_router(auth.router)
app.include_router(warrants.router)
app.include_router(portfolio.router)
app.include_router(credit.router)
app.include_router(chat.router)
app.include_router(news_impact.router)
app.include_router(regime.router)
# Future:
# app.include_router(analyst.router)   ← Phase P1-3
```

Each router file:
```python
router = APIRouter(tags=["domain-name"])
```

---

## 8. Async vs Sync Routes

**Current codebase:** Mostly sync routes calling sync services.

**Rule for NEW code:**
- I/O bound (DB, HTTP, Redis): `async def` + `await`
- CPU bound (BSM matrix, XGBoost): sync route + `run_in_executor` OR background task

```python
# CPU-heavy — offload
@router.post("/api/warrants/scan/async", status_code=202)
async def scan_async(request: ScanRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(CWPricingService.run_full_scan, request.filters)
    return {"status": "accepted", "job_id": "..."}
```

**Never:** Block event loop with 10+ second pandas operations in `async def` route.

---

## 8. WebSocket Convention

Endpoint: `WS /api/ws`  
Handler: `src/api/websocket.py`

**Message format:**
```json
{
  "type": "cw_update|regime_change|signal_alert",
  "payload": { ... },
  "timestamp": "2026-06-26T09:15:00+07:00"
}
```

**Phase 5 frontend:** `useWebSocket` hook connects here for live Greeks updates.

---

## 9. Endpoints TO CREATE

### P1-2: Credit Risk Batch Scan
```
GET /api/credit-risk/scan?tickers=VNM,FPT,VCB&limit=50
```
- Max 50 tickers per request
- Uses per-ticker cache from `CreditRiskService`
- Response: `{ "status": "ok", "results": [{ ticker, pd_score, risk_label, ... }] }`

### P1-3: AI Analyst Prompt
```
GET /api/analyst-prompt/{ticker}
GET /api/analyst-prompt/{ticker}?cw_symbol=CWXYZ123
```
- Pulls CW data from `CWPricingService`
- Injects into prompt template (see `Analyst_Prompt.md`)
- Response: `{ "prompt": "...", "data_injected": {...}, "cw_candidates": [...] }`

---

## 10. OpenAPI / Swagger

Auto-generated at `/docs`. Keep `description` and `Query(description=...)` filled for all public endpoints.

**Phase P3 — Versioning:**
- Prefix new breaking changes with `/api/v2/`
- Keep `/api/v1/` or unversioned routes stable for 6 months

---

## 11. Route Checklist (New Endpoint)

Before merging a new route:
- [ ] Business logic in `service.py`, not route
- [ ] Pydantic validation on inputs
- [ ] Appropriate HTTP status codes
- [ ] Rate limit applied if expensive
- [ ] Auth/subscription check if VIP feature
- [ ] OpenAPI description filled
- [ ] Test in `tests/test_api_*.py`
- [ ] Added to `system/02_Project_Index.md` API map
