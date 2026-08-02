# 01. COVERED WARRANTS (CW) PRICING BIBLE
**Domain:** `src/modules/cw_pricing`
**Focus:** Analytical Pricing, Greeks, Implied Volatility (IV), and ML Parameter Tuning.

## 1. Market Context & Baseline Model
* **Asset Class:** Vietnamese Covered Warrants (CW) based on VN30 components.
* **Execution Style:** European Options (exercised only at maturity).
* **Baseline Engine:** The Black-Scholes-Merton (BSM) model is the absolute source of truth in `pricing_core.py`. 

## 2. Mathematical Definitions (Strict)
All Python implementations must strictly reflect these formulas. Do not use approximations.

### 2.1 The Black-Scholes Formulas
For a Call Warrant ($C$), the theoretical price is calculated as:
$$C = \frac{1}{\text{Ratio}} \left[ S \cdot N(d_1) - K \cdot e^{-rT} \cdot N(d_2) \right]$$

Where:
* $S$ = Current price of the underlying asset (VN30 stock).
* $K$ = Strike price.
* $T$ = Time to maturity (annualized). If testing without live data, default to $T = 0.25$ (3 months).
* $r$ = Risk-free interest rate (annualized).
* $\sigma$ = Historical or Implied Volatility.
* $N(x)$ = Cumulative standard normal distribution.

The parameters $d_1$ and $d_2$ are:
$$d_1 = \frac{\ln(S/K) + (r + \frac{\sigma^2}{2})T}{\sigma \sqrt{T}}$$
$$d_2 = d_1 - \sigma \sqrt{T}$$

### 2.2 The Greeks
The engine must output a complete Greeks matrix for risk management. Use these exact derivatives:
* **Delta ($\Delta$):** Must be adjusted by the conversion ratio.
  $$\Delta = \frac{\partial C}{\partial S} = \frac{N(d_1)}{\text{Ratio}}$$
* **Gamma ($\Gamma$):** $$\Gamma = \frac{\partial^2 C}{\partial S^2} = \frac{N'(d_1)}{S \sigma \sqrt{T} \cdot \text{Ratio}}$$
* **Theta ($\Theta$):** $$\Theta = \frac{\partial C}{\partial T} = \frac{1}{\text{Ratio}} \left[ -\frac{S N'(d_1) \sigma}{2 \sqrt{T}} - r K e^{-rT} N(d_2) \right]$$
* **Vega ($\nu$):** (Note: Vega is expressed per 1% change in volatility)
  $$\nu = \frac{\partial C}{\partial \sigma} = \frac{S \sqrt{T} N'(d_1)}{\text{Ratio}}$$

## 3. Machine Learning Enhancement (GA-WOA)
* **Objective:** `pricing_core_enhanced.py` uses the Genetic Algorithm - Whale Optimization Algorithm (GA-WOA) to calibrate the Implied Volatility ($\sigma_{IV}$) by minimizing the Mean Squared Error (MSE) between the BSM theoretical price and the actual market price of the CW.
* **Constraint:** GA-WOA is an optimization wrapper. It MUST invoke the analytical equations above during its fitness evaluation. It must NEVER bypass the BSM math.

## 4. IV vs HV — Volatility Arbitrage (Critical Signal)

**IV/HV ratio** is the most important pre-filter for CW buying decisions.

| Ratio | Label | Trading Action |
|-------|-------|----------------|
| IV/HV > 1.30 | OVERPRICED | Strong deprioritize — implied vol 30%+ above realized |
| IV/HV 1.10–1.30 | FAIR TO EXPENSIVE | Caution — only buy with strong catalyst |
| IV/HV 0.90–1.10 | FAIR VALUE | Proceed to Delta/Score filters |
| IV/HV < 0.90 | CHEAP VOL | Priority boost — vol is cheap vs history |

**Implementation:**
- IV: solved via Newton-Raphson in `estimate_implied_volatility()` (`pricing_core.py`)
- HV 20d: cached in `configs/underlying_hv_cache.json`, refreshed daily 16:00
- Ratio exposed in `/api/warrants/opportunities` response as `iv_hv_ratio`
- Analyst prompt Bước 0 MUST rank by this ratio (see `Analyst_Prompt.md`)

**Hard gate in pricing_core.py:** Smart Spread Check — reject CW if `(ask-bid)/mid > 15%`.

---

## 5. GEX Engine

**File:** `models/gex_engine.py`

Gamma Exposure (GEX) measures market maker hedging pressure from CW issuer's book.

- Positive GEX → price pinning near strikes
- Negative GEX → vol expansion, larger moves possible

Expose `gex_score` in opportunities API when available.  
Analyst prompt Bước 2C requires GEX interpretation when data present.

---

## 6. Discrete Dividends (P0-2 — Not Yet Integrated)

**File:** `models/discrete_dividends.py` — EXISTS but NOT imported by pricing path.

Vietnamese stocks pay large lump-sum cash dividends. Continuous yield `q` in BSM underestimates the spot drop at ex-date.

**Functions available:**
- `calculate_dividend_adjusted_spot(S, r, dividends, T)` — PV-adjusted spot
- `binomial_tree_dividend_adjusted(...)` — CRR tree with discrete dividends

**Current pricing path:** Uses continuous dividend yield `q` in `pricing_core.py`.

**Fix options (P0-2):**
- Option A: Add `use_discrete_dividends: bool` flag → call adjusted spot before BSM
- Option B: Defer with documented reason in `pricing_core_enhanced.py`

**Rule:** Do NOT delete `discrete_dividends.py` — it is planned integration.

---

## 7. SABR Volatility Surface

**File:** `models/sabr_vol_surface.py`

SABR model for volatility smile/skew across strikes. Used in enhanced pricing and backtest evaluation.

---

## 8. Service Layer & API

**File:** `service.py` (~20KB) — largest module, orchestrates all pricing.

**Key routes (`src/api/routes/warrants.py`):**
| Endpoint | Purpose |
|----------|---------|
| `GET /api/warrants/opportunities` | Main CW table — CORE frontend data |
| `POST /api/warrants/greeks` | On-demand Greeks calculation |
| `POST /api/warrants/scan` | Filtered scan |
| `GET /api/warrants/{symbol}/simulate` | P/L matrix (VIP) |
| `GET /api/warrants/{symbol}/history` | IV/HV history |
| `POST /api/warrants/{symbol}/deep-analysis` | AI deep analysis |

**TO CREATE:** `GET /api/analyst-prompt/{ticker}` — see `Analyst_Prompt.md`

---

## 9. Backtest Module

**Directory:** `backtest/` (13 files)

Key files:
- `performance_evaluator.py` (~41KB) — comprehensive performance metrics
- `ranker.py` — CW ranking logic
- `risk_engine.py` — portfolio risk
- `opt_cw_grid_search.py` — parameter optimization

Backtest scripts are standalone — not imported by service layer in production hot path.

---

## 10. Code Implementation Rules
* **Vectorization:** When pricing a matrix of CWs, use `numpy` or `torch` vectorization. Avoid Python `for` loops to prevent severe latency during live tick data processing.
* **Data Types:** Use `float64` for all internal pricing calculations to prevent floating-point underflow on Deep Out-of-the-Money (OTM) warrants.
* **Conversion ratio:** All Greeks MUST be divided by CW conversion ratio for Vietnamese market convention.
* **Theta display:** Express as absolute value AND as `% of price per day` for user-facing output.
* **Market cache:** Use `src/infra/market_cache.py` session-aware cache — do not fetch live prices outside trading hours unnecessarily.