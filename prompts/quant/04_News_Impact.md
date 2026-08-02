# 04. NEWS IMPACT & SENTIMENT BIBLE
**Domain:** `src/modules/news_impact`
**Focus:** NLP, RAG, Financial Sentiment Analysis, and Event-Driven Signals.

## 1. Core Pipeline Strict Sequence
The News Impact module operates as an event-driven pipeline. AI Agents MUST strictly follow this execution order when modifying or running the pipeline. Do NOT reorder these steps:
1. `prepare`: Fetch raw news, scrape articles, and clean HTML/text.
2. `align`: Time-align news timestamps with VN30 tick data.
3. `calculate`: Run NLP models (Sentiment analysis, FinBERT) to generate scores $[-1, 1]$.
4. `test`: Validate signals against historical price movements.
5. `report`: Generate summaries and metadata for the AI Committee.

## 2. Model & RAG Constraints
* **Vector Store:** Use `pgvector` within PostgreSQL to store embeddings of financial reports. Do not introduce a separate vector database unless explicitly approved.
* **Embeddings:** Standardize on a specific embedding model (e.g., `text-embedding-3-small` or a local FinBERT variant). Do not mix embedding dimensions.
* **Prompt Injection:** When generating summaries using LLMs, always sanitize inputs.
* **Sentiment Output:** The final sentiment signal must be a normalized vector (e.g., `{"bullish": 0.6, "bearish": 0.1, "neutral": 0.3}`).

## 3. Service Layer (Production — Verified 26/06/2026)

**File:** `src/modules/news_impact/service.py`

**Public methods:**
| Method | Returns | Used By |
|--------|---------|---------|
| `get_news_impact(ticker, days, run_pipeline)` | Summary + optional pipeline | API route |
| `get_ml_signal(ticker)` | `{outperform_probability, features, model_loaded}` | AI Committee L3 |
| `get_ticker_sentiment_score(ticker, days)` | float [-1, 1] | AI Committee L3 |
| `run_full_pipeline(symbol, ...)` | Full B1→B2→B3 pipeline | API `/pipeline` |
| `run_event_study(symbol, event_date)` | Single event CAR study | API `/pipeline` |

**ML model:** `data/processed/news_ml_model.joblib` — loaded lazily via `_load_model()`.

**Cache:** In-memory dict, TTL 1800s (30 min). Migrate to Redis key `news:sentiment:{ticker}` in Phase 6.

---

## 4. API Routes (`src/api/routes/news_impact.py`)

| Endpoint | Purpose |
|----------|---------|
| `GET /api/news-impact/{ticker}` | Lightweight sentiment summary |
| `GET /api/news-impact/{ticker}/ml-signal` | ML outperform probability |
| `GET /api/news-impact/{ticker}/sentiment` | Sentiment score + label |
| `GET /api/news-impact/{ticker}/pipeline` | Full pipeline (heavy) |

---

## 5. Integration with AI Committee

**File:** `src/modules/trading_engine/ai_committee_service.py` lines 232-233:

```python
ml_signal = NewsImpactService.get_ml_signal(underlying)
sentiment_score = NewsImpactService.get_ticker_sentiment_score(underlying, days=30)
```

**Layer 3 — Macro Sentiment:**
- ML signal: outperform probability vs benchmark
- Sentiment: 30-day news sentiment score
- Combined into Gemini consensus prompt

**Rules:**
- News Impact NEVER executes trades directly
- Never call LLM inside `get_ml_signal()` — use pre-trained joblib model
- Cache sentiment 5-15 min (currently 30 min in-memory)
- If model not loaded: return `{"model_loaded": false, "signal": "NEUTRAL"}` gracefully

---

## 6. Pipeline Files (Flat Structure — Refactor P4)

```
src/modules/news_impact/
├── news_step1_prepare.py    ← etl/ (planned move)
├── news_step2_align.py
├── news_step3_calculate.py
├── news_step5_report.py
├── news_step6_train_ml.py
├── news_step7_cw_basket.py
├── news_step8_cw_car.py
├── news_step9_dual_report.py
├── pipeline.py              ← orchestrator
├── forecast_engine.py
├── exposure_assessor.py
└── reality_checker.py
```

Steps are callable from `service.py` — not notebook-only scripts.

---

## 7. Testing Requirements

**File TO CREATE:** `tests/test_news_impact.py`

```python
def test_sentiment_score_range():
    score = NewsImpactService.get_ticker_sentiment_score("VNM", days=30)
    assert -1.0 <= score <= 1.0

def test_ml_signal_structure():
    signal = NewsImpactService.get_ml_signal("VNM")
    assert "outperform_probability" in signal or "model_loaded" in signal
```

Mock news fetcher — never hit live news APIs in unit tests.