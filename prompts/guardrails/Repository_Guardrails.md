# REPOSITORY GUARDRAILS & ANTI-PATTERNS
**Priority:** HIGHEST (Override all other instructions if conflicts arise)

## 1. Naming & Schema Strict Rules
* **Database Objects:** Always use the singular `Fund` for base objects, library compatibility, and ORM mapping. NEVER use `Funds`.
* **Warrant Tickers:** When writing tests or validation scripts for covered warrants, use valid formats (e.g., `CMWG2520`). Do NOT default to deprecated or invalid test tickers like `CMWG2602`.

## 2. Quantitative Model Constraints
* **Maturity Parameter ($T$):** In American/European Put Option calculations and Black-Scholes baseline testing, the default maturity parameter $T$ must be set to 3 ($T=3$), unless explicitly dynamically fetched from the exchange. Do not use $T=5$ as a default fallback.
* **Pricing Overwrites:** Never replace the analytical Black-Scholes pricing function with a pure Machine Learning output. ML (like GA-WOA) is strictly an *enhancement* layer to adjust parameters or predict trends, not a replacement for fundamental Greeks ($\Delta, \Gamma, \Theta, \nu, \rho$).

## 3. Data Source Integrity
* **Feed Segregation:** When processing historical or real-time tick data, explicitly tag the data source. System logic must differentiate between data scraped from a personal app/database and official institutional API feeds (e.g., SSI). Do not mix these data points in the same analysis without normalization.
* **Processed Data:** Never write code that directly overwrites files in `/data/processed` without a backup snapshot mechanism.

## 4. Architectural Anti-Patterns (NEVER DO THESE)
* **Bypassing Service Layer:** Controllers (`/api`) or Trading Engines must never query the PostgreSQL/DuckDB database directly. Always go through `service.py`.
* **Modifying Artifacts:** Files in `/artifacts` (`.pkl`, `.pt`) are read-only in production. If a model like Attention-GRU is retrained, it must be versioned (e.g., `model_v2.pt`), not overwritten.
* **Direct Logic in Routes:** FastAPI routes must only handle HTTP requests/responses and dependency injection. Zero business logic is allowed in `router.get()` or `router.post()`.