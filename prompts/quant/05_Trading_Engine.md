# 05. TRADING ENGINE & AI DECISION BIBLE
**Domain:** `src/modules/trading_engine`

## 1. Engine Architecture
The Trading Engine is the execution layer of FINVISTA. It does not calculate prices; it consumes signals from `cw_pricing`, `regime_analysis`, and `news_impact`.

### Core Components:
1. **Signal Aggregator:** Collects normalized data arrays.
2. **AI Committee:** The central decision logic.
3. **Paper Trader (Execution):** Simulates the market execution.
4. **Risk Manager:** Checks exposure and portfolio limits before execution.

## 2. AI Committee & Machine Learning Integration
The decision-making process relies on advanced predictive models rather than simple moving averages.

* **Hybrid Stacking Ensemble:** The primary architecture for generating consensus signals. The engine must query the `artifacts/` directory to load the correct `.pkl` or `.pt` models.
* **GA-WOA Optimization:** Used for fine-tuning entry/exit thresholds and predicting VN30 price trends. Code interacting with this must be highly optimized, utilizing asynchronous execution to prevent blocking the main trading loop.
* **Attention-GRU:** Time-series forecasting for VN30 components. Ensure sequence lengths and tensor shapes strictly match the trained model's requirements during inference.

## 3. Paper Trading & Backtesting Realism
To ensure backtests and paper trades reflect the real Vietnamese market:
* **Transaction Fees & Taxes:** MUST be explicitly calculated and deducted from the PnL for every single trade. Never execute a "frictionless" backtest.
* **Slippage:** Apply a dynamic slippage model based on the order book depth (if using SSI data) or a fixed penalty (if using personal app data).
* **Tick Size Compliance:** Order prices must be rounded to the nearest valid tick size for the specific VN30 stock or Covered Warrant.

## 4. Execution Flow
1. Fetch current Portfolio state (`Fund` base entity).
2. Fetch current Regime (Bull/Bear/Volatility).
3. Evaluate AI Committee signals.
4. If `Action == BUY/SELL`:
   a. Check Risk Limits.
   b. Calculate estimated fees.
   c. Log intent to PostgreSQL.
   d. Execute via Paper Trader (or real broker API in production).

---

## 5. Orchestrator (`orchestrator.py`)

**Main loop:** Scans opportunities → filters buy signals → AI Committee approval → paper execution.

**Async pattern (FIXED 26/06/2026):**
```python
# ✅ CORRECT — line 103
approved_signals = asyncio.run(self._process_signals_with_ai(buy_signals[:3]))

# ❌ NEVER reintroduce
asyncio.get_event_loop().run_until_complete(...)  # deprecated Python 3.10+
```

**Constraint:** Orchestrator has NO internal pricing logic — consumes `cw_pricing` service output only.

**Data contract gap (P3):** Add Pydantic schema validation when receiving CW Pricing data — schema change in cw_pricing will break orchestrator silently.

---

## 6. AI Committee Layers (Detailed)

**File:** `ai_committee_service.py`

| Layer | Source | Data |
|-------|--------|------|
| L1 CW Signals | cw_pricing | score, delta, iv_hv_ratio, signal |
| L2 Regime | regime_analysis | HMM bias, confidence |
| L3 Macro Sentiment | news_impact | `get_ml_signal()` + `get_ticker_sentiment_score()` |
| L4 Vision Skeptic | Gemini | chart pattern analysis |

**Layer 3 integration (verified):**
```python
ml_signal = NewsImpactService.get_ml_signal(underlying)
sentiment_score = NewsImpactService.get_ticker_sentiment_score(underlying, days=30)
```

---

## 7. Paper Trader Testing Requirements

**File TO CREATE:** `tests/test_paper_trader.py`

Required test cases:
- Entry at ask price (not mid)
- Exit at bid price (not mid)
- Transaction fee deducted: HOSE fee schedule
- Tax on sell applied
- Position size respects portfolio limits
- Cannot buy with insufficient cash
- Tick size rounding on order price

```python
def test_paper_trader_deducts_fees():
    trader = PaperTrader(initial_cash=100_000_000)
    trader.buy("CWG1234", qty=1000, price=1500)
    trader.sell("CWG1234", qty=1000, price=1800)
    # assert final_cash != initial + (1800-1500)*1000  ← must include fees
    assert trader.total_fees_paid > 0
```