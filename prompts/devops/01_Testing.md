# 01. TESTING & VALIDATION BIBLE
**Framework:** `pytest`
**Directory:** `tests/`
**Philosophy:** Financial logic fails silently. Tests must be mathematically rigorous.

## 1. Unit Testing Rules (The Quant Tests)
* **Location:** `tests/modules/cw_pricing/`
* **Rule 1:** When testing the BSM model, hardcode the inputs and the expected outputs from a known textbook or Bloomberg terminal reference. 
  * Example: If $S=100$, $K=100$, $T=1$, $r=0.05$, $\sigma=0.2$, the Call price must assert to `10.4506`.
* **Rule 2:** Test edge cases, specifically:
  * Time to maturity $T \rightarrow 0$ (Expiration day behavior).
  * Extreme Volatility $\sigma \rightarrow 0$ or $\sigma > 1.5$.
  * Deep ITM (In-The-Money) and Deep OTM (Out-Of-The-Money).

## 2. Integration & Engine Testing
* **Location:** `tests/modules/trading_engine/`
* **Paper Trader Validation:** You MUST write tests to ensure that transaction fees and slippage are correctly deducted from the simulated portfolio balance.
  * **Anti-Pattern:** A test where `Final Balance = Initial Balance + (Sell Price - Buy Price) * Volume`.
  * **Correct Pattern:** `Final Balance = Initial Balance + (Sell Price - Buy Price) * Volume - Total Fees`.
* **Mocking:** NEVER hit live institutional APIs (like SSI) or the actual PostgreSQL database during unit/integration tests. Use `pytest-asyncio` and `unittest.mock.AsyncMock` to fake API feeds and database sessions.

## 3. Data Integrity & Fixtures
* Store dummy tick data and mocked JSON responses in `tests/fixtures/`.
* When testing the `news_impact` module, mock the LLM/Embedding calls. Tests must not incur OpenAI/Gemini API billing costs.

---

## 4. Current State vs Target (26/06/2026)

**Current:** 1 test file — `tests/test_regime_portfolio.py`  
**Target:** 15+ tests before Phase 8 deploy  
**Roadmap claim "15/15 done" is INCORRECT** — treat as target, not current state.

---

## 5. Required Test Files (Priority Order)

| Priority | File | Tests | Blocks |
|----------|------|-------|--------|
| P0 | `tests/test_kalman_filter.py` | estimate(), signal enum, noisy series | Regime API fix |
| P2 | `tests/test_pricing_core.py` | BSM price, 5 Greeks, IV solver, T→0 | CW pricing changes |
| P2 | `tests/test_paper_trader.py` | entry, exit, fee deduction, slippage | Trading engine |
| P2 | `tests/test_credit_health.py` | 404, cache hit, pd_score bounds | Credit API |
| P2 | `tests/test_news_impact.py` | sentiment range, ml_signal structure | News module |
| P2 | `tests/test_regime_routes.py` | 3 regime endpoints via TestClient | Regime API |
| P3 | `tests/test_api_auth.py` | register, login, me, 401 | Auth flow |
| P2 | `tests/conftest.py` | FastAPI TestClient, mock SessionLocal | All integration tests |
| P3 | `tests/test_redis_client.py` | fallback when unavailable, set/get JSON | Phase 6 Redis |

---

## 6. conftest.py Template

```python
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

@pytest.fixture
def client():
    from src.api.main import app
    with TestClient(app) as c:
        yield c

@pytest.fixture
def mock_db_session():
    with patch("src.core.database.SessionLocal") as mock:
        session = MagicMock()
        mock.return_value.__enter__ = lambda s: session
        mock.return_value.__exit__ = lambda s, *a: None
        yield session
```

---

## 7. BSM Reference Test (Mandatory)

```python
# tests/test_pricing_core.py
import pytest
from src.modules.cw_pricing.models.pricing_core import black_scholes_call

def test_bsm_call_textbook_reference():
    """Hull/ Bloomberg reference: S=100, K=100, T=1, r=0.05, sigma=0.2 → C≈10.4506"""
    price = black_scholes_call(S=100, K=100, T=1, r=0.05, sigma=0.2, q=0.0)
    assert abs(price - 10.4506) < 0.01

def test_bsm_expiry_day():
    """T→0: call price → max(S-K, 0)"""
    price = black_scholes_call(S=110, K=100, T=1e-10, r=0.05, sigma=0.2, q=0.0)
    assert abs(price - 10.0) < 0.01
```

---

## 8. CI Test Command

```bash
pytest tests/ -v --tb=short --cov=src/modules --cov-report=term-missing
```

**Minimum coverage target:** 85% for `/modules` (Phase 8 gate).  
**Current coverage:** Near 0% — prioritize P0/P2 files first.

---

## 9. Test Anti-Patterns (See also `guardrails/Anti_Patterns.md`)

- ❌ Live API calls in unit tests
- ❌ Frictionless PnL assertions (no fee deduction)
- ❌ Financial logic change with zero test update
- ❌ Tests that depend on specific SQLite data existing (use fixtures/mocks)