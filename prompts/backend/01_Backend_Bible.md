# 01. BACKEND BIBLE
**Framework:** FastAPI (Python)
**Focus:** Concurrency, Type Safety, and Domain-Driven Design (DDD).

## 1. General Conventions
* **Typing:** 100% strict type hinting is mandatory (`mypy` compliant). Use `Pydantic` V2 for all data validation.
* **Asynchrony:** All I/O bound operations (Database, Redis, API calls) MUST use `async`/`await`. CPU-bound operations (e.g., Heavy Black-Scholes matrix math, Attention-GRU inference) MUST be offloaded to `ThreadPoolExecutor` or background worker tasks (Celery).
* **Configuration:** Handled exclusively via `pydantic-settings`. No hardcoded credentials or model paths.

## 2. API Design & Routing
* **Thin Routes:** FastAPI router functions (`src/api/routes`) must contain ZERO business logic. They only parse requests, pass dependencies to the Service layer, and return formatted responses.
* **Dependency Injection:** Utilize FastAPI's `Depends()` for database sessions, authentication, and service instantiation.
* **Response Format:** Standardize all JSON responses:
    ```json
    {
      "status": "success|error",
      "data": { ... },
      "message": "Optional context"
    }
    ```

## 3. Database & ORM (PostgreSQL & Alembic)
* **SQLAlchemy 2.0:** Use the 2.0 style syntax (e.g., `select()`, `session.execute()`).
* **Location:** `src/core/database.py` (NOT `src/infra/database/` — that path does not exist).
* **Default:** SQLite at `data/finvista.db`. Override with `DATABASE_URL` env for PostgreSQL.
* **Naming Convention:** Tables are strictly singular or follow the exact domain nomenclature (e.g., `Fund` over `Funds` to prevent ORM mapping errors).
* **Migrations:** NEVER manually edit the database schema. All changes must be generated via Alembic (`alembic revision --autogenerate`). Never modify an applied migration file; create a new one.
* **PostgreSQL connect_args:** Remove `check_same_thread` when not using SQLite:
  ```python
  connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
  ```

## 4. The Service Layer
* The Service layer (`src/modules/{domain}/service.py`) acts as the conductor.
* **Rule:** If `trading_engine` needs CW data, its service calls `cw_pricing.service.get_current_greeks()`. It NEVER imports `cw_pricing.pricing_core`.

## 5. Caching Strategy
* **Redis:** Cache pure analytical computations (e.g., baseline Greeks for highly liquid VN30 components) using short TTLs (e.g., 5-15 seconds depending on tick frequency).
* Invalidate cache explicitly upon significant market events (event-driven via `news_impact`).