# 03. REGIME ANALYSIS BIBLE
**Domain:** `src/modules/regime_analysis`  
**Focus:** HMM market states, GARCH volatility, Kalman trend, multi-TF momentum

---

## 1. Module Overview

Regime Analysis detects **market state** (bull/bear/sideways/volatility expansion) to inform CW trading bias.

**Output consumers:**
- AI Committee Layer 2 (`ai_committee_service.py`)
- Frontend Regime Monitor (Phase 5.3)
- Trading orchestrator entry/exit gating

**Must output normalized signals** — probability vectors or clear enum labels, never raw unbounded floats without context.

---

## 2. Directory Structure

```
src/modules/regime_analysis/
├── service.py
└── indicators/
    ├── hmm_regime.py              ← HMM 4-state VNINDEX model
    ├── garch_volatility_forecaster.py  ← GARCH(1,1) 1-step forecast
    ├── garch_evt_var.py           ← GARCH + Extreme Value Theory VaR
    ├── kalman_filter.py           ← KalmanFilterPrice (P0 BUG — missing wrapper)
    ├── regime_detector.py         ← RegimeDetector composite
    ├── multi_tf_ema.py            ← Multi-timeframe EMA signals
    └── volatility_models.py       ← Realized volatility
```

---

## 3. HMM 4-State Model

**File:** `indicators/hmm_regime.py`  
**Function:** `calculate_vnindex_regime(days=1250)`

**States:**
| State | Label | CW Bias |
|-------|-------|---------|
| 0 | BULLISH_VOL_EXPANSION | LONG CW — vol rising in uptrend |
| 1 | BULLISH_LOW_VOL | LONG CW — steady uptrend |
| 2 | BEARISH_CRISIS | AVOID / SHORT |
| 3 | SIDEWAYS | NEUTRAL — wait for clarity |

**Output:**
```json
{
  "regime": "BULLISH_LOW_VOL",
  "confidence": 0.82,
  "bias": "LONG_CW",
  "description": "...",
  "state_probabilities": [0.05, 0.82, 0.08, 0.05]
}
```

**Data:** VNINDEX 5-year daily returns, Gaussian HMM (hmmlearn).

---

## 4. GARCH Volatility

**File:** `indicators/garch_volatility_forecaster.py`

GARCH(1,1):
$$\sigma_t^2 = \omega + \alpha \epsilon_{t-1}^2 + \beta \sigma_{t-1}^2$$

**Usage:**
```python
forecaster = GARCHVolatilityForecaster()
result = forecaster.forecast(ticker="VNM", days=252)
# Returns: { "forecast_vol": 0.28, "current_vol": 0.25, "regime": "EXPANDING" }
```

**EVT extension:** `garch_evt_var.py` — tail risk VaR at 95%/99% confidence.

---

## 5. Kalman Filter — P0 BUG

**Current state (BROKEN):**

`src/api/routes/regime.py` line 144-146:
```python
from src.modules.regime_analysis.indicators.kalman_filter import KalmanFilter
kf = KalmanFilter()
result["indicators"]["kalman_trend"] = kf.estimate(ticker=ticker_clean, days=days)
```

`kalman_filter.py` ONLY contains:
```python
class KalmanFilterPrice:
    def update(self, measurement: float) -> float: ...
```

**No `KalmanFilter` class. No `estimate()` method.**

**Fix spec (P0-1):**

Add to `kalman_filter.py`:

```python
class KalmanFilter:
    """High-level wrapper: fetch prices → apply KalmanFilterPrice → return trend signal."""

    def __init__(self, process_variance: float = 1e-5, measurement_variance: float = 1e-3):
        self._kf = KalmanFilterPrice(process_variance, measurement_variance)

    def estimate(self, ticker: str, days: int = 252) -> dict:
        prices = self._fetch_close_prices(ticker, days)  # use existing data fetcher
        if len(prices) < 10:
            return {"error": f"Insufficient data for {ticker}", "signal": "UNKNOWN"}

        filtered = []
        kf = KalmanFilterPrice()
        for p in prices:
            filtered.append(kf.update(p))

        slope = (filtered[-1] - filtered[-20]) / filtered[-20] if len(filtered) >= 20 else 0
        signal = "BULLISH" if slope > 0.02 else "BEARISH" if slope < -0.02 else "NEUTRAL"

        return {
            "ticker": ticker.upper(),
            "current_trend": round(filtered[-1], 2),
            "slope_20d": round(slope, 4),
            "signal": signal,
            "filtered_series": filtered[-30:],  # last 30 points for chart
        }

    def _fetch_close_prices(self, ticker: str, days: int) -> list:
        # Reuse vnstock or DB — match pattern from multi_tf_ema.py
        ...
```

**Acceptance criteria:**
- [ ] `GET /api/regime/VNM/indicators` → `kalman_trend` without `"error"` key
- [ ] `tests/test_kalman_filter.py` passes

---

## 6. RegimeDetector

**File:** `indicators/regime_detector.py`

Composite detector combining HMM + momentum + vol:

```python
detector = RegimeDetector()
regime_data = detector.detect(ticker="VNM", lookback_days=252)
# { "regime": "BULLISH_LOW_VOL", "confidence": 0.75, "components": {...} }
```

Used in `/api/regime/{ticker}` for `regime_recommendation` string.

---

## 7. Multi-TF EMA

**File:** `indicators/multi_tf_ema.py`

EMA crossovers across timeframes (daily, weekly proxy):
- Fast EMA / Slow EMA ratio
- Signal: GOLDEN_CROSS / DEATH_CROSS / NEUTRAL

---

## 8. API Routes

**File:** `src/api/routes/regime.py` — ✅ EXISTS (audit cũ sai)

| Endpoint | Returns |
|----------|---------|
| `GET /api/regime/market` | VNINDEX HMM state |
| `GET /api/regime/{ticker}` | GARCH + EMA + RegimeDetector + recommendation |
| `GET /api/regime/{ticker}/indicators` | Full indicator bundle (GARCH EVT, Kalman, Realized Vol) |

**Query params:**
- `days`: int, default 252, range [60, 1250]

**Error handling:** Partial failures return `{"error": "..."}` per indicator — route still returns 200 with partial data.

---

## 9. Integration with AI Committee

Layer 2 in `ai_committee_service.py`:
- Fetches market regime via HMM
- Passes `bias` (LONG_CW / AVOID / NEUTRAL) to consensus prompt
- Low confidence (< 0.5) → downgrade signal strength

---

## 10. Frontend Spec (Phase 5.3)

**Page:** `/regime`

Components:
1. **Market Regime Badge** — large, color-coded from `/api/regime/market`
2. **HMM Timeline** — historical state chart (needs historical endpoint — future)
3. **GARCH Vol Chart** — per-ticker from `/api/regime/{ticker}`
4. **Ticker Search** — autocomplete VN30 components

---

## 11. Testing

**Existing:** `tests/test_regime_portfolio.py`

**TO CREATE:** `tests/test_regime_routes.py`
```python
def test_market_regime_endpoint(client):
    r = client.get("/api/regime/market")
    assert r.status_code == 200
    assert "regime" in r.json()

def test_ticker_regime_endpoint(client):
    r = client.get("/api/regime/VNM?days=252")
    assert r.status_code == 200
    assert r.json()["ticker"] == "VNM"

def test_kalman_not_error(client):
    r = client.get("/api/regime/VNM/indicators")
    kalman = r.json()["indicators"]["kalman_trend"]
    assert "error" not in kalman  # P0 fix required for this to pass
```

---

## 12. Code Rules

1. State probabilities must sum to ~1.0 (±0.01 tolerance)
2. GARCH forecast must handle insufficient data gracefully (< 60 days)
3. Never block API > 10s — cache market regime 1 hour (Redis Phase 6)
4. KalmanFilter must reuse existing price fetcher — no duplicate vnstock calls
5. All ticker params: `.upper().strip()`

---

## 13. Scripts

| Script | Purpose |
|--------|---------|
| `scripts/model_training/train_ml_regime.py` | Train XGBoost regime classifier |
| `scripts/model_training/predict_ml_regime.py` | Inference |
| `scripts/model_training/visualize_kairos_regimes.py` | Visualization |
| `scripts/model_training/backtest_regime_strategies.py` | Strategy backtest |

Scripts are standalone — not imported by service layer.
