# ANTI-PATTERNS — NEVER DO THESE
**Priority:** HIGHEST — violations must be rejected in code review.

Companion: `Repository_Guardrails.md`

---

## 1. Architecture Anti-Patterns

### ❌ Business logic in routes
```python
# NEVER
@router.get("/api/warrants/opportunities")
def get_opportunities():
    df = pd.read_csv("data/processed/cw.csv")  # REJECT
    df["score"] = df.apply(lambda r: compute_score(r), axis=1)  # REJECT
    return df.to_dict()
```
**Fix:** Move to `CWPricingService.get_opportunities()` in `service.py`.

### ❌ Cross-module internal imports
```python
# NEVER in trading_engine/
from src.modules.cw_pricing.models.pricing_core import calculate_greeks  # REJECT

# CORRECT
from src.modules.cw_pricing.service import CWPricingService
greeks = CWPricingService.get_greeks(symbol)
```

### ❌ Importing scripts into modules
```python
# NEVER
from scripts.model_training.train_ml_regime import train  # REJECT
```
Scripts in `scripts/` are standalone CLI tools only.

### ❌ Direct DB queries outside service/database layer
```python
# NEVER in routes or trading_engine
db = SessionLocal()
rows = db.query(CompanyDistressAnalysis).all()  # REJECT unless in service.py
```

---

## 2. Quantitative Anti-Patterns

### ❌ ML replaces Black-Scholes
```python
# NEVER
def price_cw(S, K, T, r, sigma):
    return ml_model.predict([[S, K, T, r, sigma]])[0]  # REJECT — no Greeks, no interpretability
```
ML (GA-WOA, XGBoost) adjusts **parameters** or **signals** — never replaces BSM equations.

### ❌ Frictionless paper trading
```python
# NEVER
pnl = (sell_price - buy_price) * quantity  # REJECT — no fees

# CORRECT
pnl = (sell_price - buy_price) * quantity - transaction_fee - tax
```

### ❌ Wrong default maturity
```python
T = 5  # REJECT — default must be T=3 for baseline tests
T = 0.25  # OK for 3-month CW if not fetching live maturity
```

### ❌ Float32 for deep OTM warrants
```python
price = np.float32(theoretical_price)  # REJECT — use float64
```

### ❌ Python for-loop over 200+ CW symbols
```python
for symbol in all_cw_symbols:  # REJECT in hot path
    price = black_scholes(S, K, T, r, sigma)
# CORRECT: numpy vectorization
prices = black_scholes_vectorized(S_arr, K_arr, T_arr, r, sigma_arr)
```

---

## 3. Data Anti-Patterns

### ❌ Mixing data sources without normalization
```python
# NEVER combine SSI live prices with Vietstock historical without tagging
df = pd.concat([ssi_live_df, vietstock_hist_df])  # REJECT
```
Always add `source` column and normalize timestamps to UTC+7.

### ❌ Overwriting processed data without backup
```python
# NEVER
df.to_csv("data/processed/market_data_snapshot.json")  # REJECT without backup
# CORRECT
shutil.copy(src, src + f".bak.{datetime.now():%Y%m%d}")
df.to_csv(src)
```

### ❌ Hardcoded model paths
```python
MODEL = "data/processed/news_ml_model.joblib"  # REJECT in multiple files
# CORRECT: single constant in config.py or module-level constant in service.py
```

---

## 4. Async Anti-Patterns

### ❌ Deprecated asyncio.get_event_loop()
```python
# NEVER (Python 3.10+)
loop = asyncio.get_event_loop()
loop.run_until_complete(coro)

# CORRECT
asyncio.run(coro)
# OR in async context:
await coro
```

### ❌ Blocking CPU work in async route
```python
@router.get("/api/warrants/scan")
async def scan():
    result = heavy_pandas_computation()  # REJECT — blocks event loop
    return result
```

---

## 5. Security Anti-Patterns

### ❌ Secrets in code or git
```python
API_KEY = "sk-abc123..."  # REJECT
TELEGRAM_TOKEN = "123456:ABC..."  # REJECT
```
Use `.env` + `pydantic-settings`. Never commit `configs/telegram_config.json` with real tokens.

### ❌ SQL injection via f-string
```python
query = f"SELECT * FROM users WHERE ticker = '{ticker}'"  # REJECT
# CORRECT: SQLAlchemy ORM or parameterized query
```

### ❌ CORS `allow_origins=["*"]` in production
Acceptable for dev. Phase 8 must restrict to `finvista.vn` domain.

---

## 6. Testing Anti-Patterns

### ❌ Hit live APIs in unit tests
```python
def test_credit_health():
    result = requests.get("https://api.vietstock.vn/...")  # REJECT
```

### ❌ Tests that assert wrong math
```python
# NEVER — frictionless PnL
assert final_balance == initial + profit  # REJECT without fee deduction
```

### ❌ No tests for financial logic changes
Any change to `pricing_core.py`, `paper_trader.py`, or `merton_engine.py` MUST include test updates.

---

## 7. Frontend Anti-Patterns (Phase 5)

### ❌ useEffect for data fetching
```typescript
// NEVER
useEffect(() => { fetch('/api/warrants/opportunities').then(...) }, [])
// CORRECT: TanStack Query
const { data } = useQuery({ queryKey: ['opportunities'], queryFn: fetchOpportunities })
```

### ❌ Re-render entire dashboard on every tick
WebSocket price update must update only the affected row/cell via `React.memo` or Zustand slice.

### ❌ Display raw float without formatting
```typescript
<span>{greeks.delta}</span>  // REJECT — shows 0.4567891234
<span>{greeks.delta.toFixed(4)}</span>  // CORRECT
```

---

## 8. Infrastructure Anti-Patterns

### ❌ Redis as required dependency without fallback
App must start and serve cached-stale data if Redis is down.

### ❌ Running FastAPI as root in Docker
```dockerfile
USER root  # REJECT in production Dockerfile
CMD uvicorn ...  # run as finvista_user
```

### ❌ Modifying applied Alembic migrations
Never edit a migration that has been applied to any environment. Create a new revision.

---

## 9. Naming Anti-Patterns

| Wrong | Correct |
|-------|---------|
| `Funds` (ORM model) | `Fund` |
| `CMWG2602` (deprecated test ticker) | `CMWG2520` or valid live symbol |
| `data/config/telegram_config.json` | `configs/telegram_config.json` |
| `src/common/` (deleted) | `src/core/` or `src/infra/` |
| `src/models/` (deleted) | `src/modules/{domain}/` |

---

## 10. Code Review Rejection Triggers

Reject PR immediately if ANY of:
1. Business logic added to `src/api/routes/`
2. BSM formula altered in `pricing_core.py` without quant review
3. `Funds` used instead of `Fund`
4. Secrets committed
5. `asyncio.get_event_loop()` introduced
6. Financial calculation change with zero test updates
7. Cross-module internal import bypassing service layer
