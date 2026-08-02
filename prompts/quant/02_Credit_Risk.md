# 02. CREDIT RISK & SYSTEMIC CONTAGION BIBLE
**Domain:** `src/modules/credit_risk`  
**Focus:** Merton structural model, XGBoost distress prediction, systemic network analysis

---

## 1. Module Overview

Credit Risk evaluates **corporate financial distress** for VN30 components and related equities.

**Two parallel tracks:**
1. **Individual credit health** — XGBoost bankruptcy probability per ticker
2. **Systemic contagion** — NetworkX graph of cross-holding / sector contagion risk

**Processing cadence:** Batch (daily/weekly) — NOT high-frequency like cw_pricing.

---

## 2. Directory Structure

```
src/modules/credit_risk/
├── service.py                    ← get_credit_health(ticker) — public API
├── models/
│   ├── merton_engine.py          ← Merton structural credit model
│   ├── merton_structural_model.py
│   ├── credit_pipeline.py        ← Full ML pipeline orchestrator
│   ├── credit_step1_filter.py    ← Step 1: filter companies
│   ├── credit_step2_crawl.py     ← Step 2: crawl financials
│   ├── credit_step3_compute_features.py
│   ├── credit_step4_label.py
│   ├── credit_step5_export.py
│   ├── credit_step6_train_model.py
│   ├── credit_step7_evaluate_market.py
│   ├── credit_step8_contagion_model.py
│   ├── credit_risk_trainer.py
│   ├── credit_risk_evaluator.py
│   ├── credit_risk_preprocessor.py
│   ├── bank_scoring.py           ← Sector-specific: banks
│   ├── fi_scoring.py             ← Financial institutions
│   └── re_scoring.py             ← Real estate sector
├── systemic/
│   ├── systemic_service.py       ← Public systemic API (30min cache)
│   └── network_builder.py        ← NetworkX graph construction
└── etl/
    ├── merton_data_ingestor.py   ← Daily Merton solver → DB
    ├── vietstock_scraper.py
    └── generate_historical_merton.py
```

---

## 3. Credit Health Service

**File:** `service.py`  
**Method:** `CreditRiskService.get_credit_health(ticker: str) -> Dict`

**Data source:** `CompanyDistressAnalysis` table in DB (SQLAlchemy)

**Output schema (preserve for API compat):**
```json
{
  "ticker": "VNM",
  "company_name": "...",
  "year": 2025,
  "pd_score": 0.08,
  "risk_label": "LOW|MEDIUM|HIGH|CRITICAL",
  "merton_dd": -2.1,
  "altman_z": 3.4,
  "financial_ratios": { ... },
  "ai_commentary": "..."
}
```

**Known gaps (P1 fixes):**
- ❌ No caching — every request hits DB + XGBoost inference
- ❌ No batch scan endpoint
- **Fix:** Add in-memory or Redis cache TTL 1800s (see `04_Redis_Convention.md`)

```python
_cache: Dict[str, Dict] = {}
_CACHE_TTL = 1800

@staticmethod
def get_credit_health(ticker: str) -> Dict[str, Any]:
    key = ticker.upper().strip()
    if _is_cache_valid(key):
        return _cache[key]["data"]
    result = CreditRiskService._compute_credit_health(key)
    _cache[key] = {"data": result, "_cached_at": datetime.now()}
    return result
```

---

## 4. Merton Structural Model

**Files:** `merton_engine.py`, `merton_structural_model.py`

Merton model treats equity as a call option on firm assets:

$$E = V \cdot N(d_1) - D \cdot e^{-rT} \cdot N(d_2)$$

Where:
- $V$ = market value of assets (solved iteratively)
- $D$ = face value of debt
- $E$ = market cap (observable)
- $DD = \frac{\ln(V/D) + (r - \sigma_V^2/2)T}{\sigma_V \sqrt{T}}$ (Distance to Default)

**Rules:**
- Asset volatility $\sigma_V$ solved via Newton-Raphson from equity volatility
- Default probability: $PD = N(-DD)$
- Daily batch via `merton_data_ingestor.py` → cache in DB

---

## 5. XGBoost Distress Model

**Training pipeline:** `credit_step6_train_model.py`  
**Evaluation:** `credit_step7_evaluate_market.py`

**Reported metrics (production model):**
- F1 Score: 74.74%
- ROC-AUC: 0.893

**Features (typical):**
- Altman Z-score components
- Debt/equity ratios
- Current ratio, quick ratio
- ROA, ROE trends
- Merton DD
- Sector dummy variables

**Inference rule:**
- Load model from `state` (loaded at startup in `src/api/state.py`)
- Never retrain in API request path
- Return 404 if ticker not in DB (excluded sector or no data)

---

## 6. Systemic Contagion

**File:** `systemic/systemic_service.py`

**Methods:**
| Method | Returns |
|--------|---------|
| `get_network_summary()` | Graph stats + top-10 propagators |
| `get_top_propagators(n)` | Ranked list by outbound influence |
| `get_ticker_contagion(ticker)` | Inbound/outbound exposure for one ticker |

**Cache:** In-memory 30 minutes (migrate to Redis Phase 6)

**API routes:** `src/api/routes/credit.py`
- `GET /api/systemic/network` — first call 20-40s (graph build)
- `GET /api/systemic/propagators?n=10`
- `GET /api/systemic/{ticker}`

**Network builder:** `network_builder.py`
- Uses sector correlations + cross-holdings
- NetworkX DiGraph
- DebtRank-style propagation scoring

**Gap (P4):** No visualization endpoint — frontend will need graph JSON or pre-rendered chart data.

---

## 7. Sector-Specific Scoring

| Sector | Scorer File | Notes |
|--------|-------------|-------|
| Banks | `bank_scoring.py` | CAR, NPL ratio, LDR |
| Financial Institutions | `fi_scoring.py` | Modified Altman |
| Real Estate | `re_scoring.py` | Asset-heavy balance sheet |
| General | `credit_risk_evaluator.py` | Default XGBoost path |

Route sector-appropriate scorer based on `sector_mapping.json` in configs.

---

## 8. API Endpoints

| Endpoint | Status | Notes |
|----------|--------|-------|
| `GET /api/credit-health/{ticker}` | ✅ Exists | Needs cache (P1-1) |
| `GET /api/systemic/network` | ✅ Exists | Expensive first call |
| `GET /api/systemic/propagators` | ✅ Exists | |
| `GET /api/systemic/{ticker}` | ✅ Exists | |
| `GET /api/credit-risk/scan` | ❌ TO CREATE | Batch multi-ticker (P1-2) |

### P1-2: Batch Scan Spec
```
GET /api/credit-risk/scan?tickers=VNM,FPT,VCB&limit=50
```
- If `tickers` omitted: return top `limit` highest PD scores from DB
- Max 50 tickers per request
- Rate limit: 10/minute
- Uses per-ticker cache

---

## 9. Integration Points

```
credit_risk/service.py
    ↓
/api/credit-health/{ticker}
    ↓
Frontend /credit dashboard (Phase 5.3)
    ↓
AI Committee Layer (optional future — credit gate for underlying)
```

**AI Committee:** Currently does NOT block trades on credit distress — future enhancement.

---

## 10. Testing Requirements

**File:** `tests/test_credit_health.py`

```python
def test_credit_health_known_ticker(mock_db):
    result = CreditRiskService.get_credit_health("VNM")
    assert "pd_score" in result
    assert 0 <= result["pd_score"] <= 1

def test_credit_health_unknown_ticker():
    with pytest.raises(HTTPException) as exc:
        CreditRiskService.get_credit_health("INVALID999")
    assert exc.value.status_code == 404

def test_credit_health_cache_hit(mock_db):
    r1 = CreditRiskService.get_credit_health("VNM")
    r2 = CreditRiskService.get_credit_health("VNM")
    assert r1 == r2  # second call from cache
```

Mock DB — never hit live PostgreSQL in unit tests.

---

## 11. Code Rules

1. **404 for missing ticker** — never return empty dict silently
2. **Sector exclusions** — some tickers excluded from model (document in response)
3. **Async batch only** — systemic network build must not block API event loop > 5s without cache
4. **No `@staticmethod` duplicate decorators** — was a bug, now fixed; do not reintroduce
5. **Singular `Fund`** for portfolio ORM references

---

## 12. Scripts

| Script | Purpose |
|--------|---------|
| `scripts/model_training/calibrate_merton.py` | Calibrate Merton parameters |
| `scripts/model_training/market_merton_scan.py` | Full market Merton scan |
| `scripts/model_training/audit_regime.py` | Regime audit (cross-module) |

Run scripts manually — never import into service layer.
