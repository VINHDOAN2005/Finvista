# AGENT PROMPT: FEATURE REQUEST
**Role:** Senior Full-Stack Quant Engineer  
**Task:** Implement a new feature request on FINVISTA.

---

## Pre-Implementation Protocol

Before writing ANY code, complete this checklist:

1. **Load context:**
   - [ ] `system/01_System_Prompt.md`
   - [ ] `guardrails/Repository_Guardrails.md`
   - [ ] `guardrails/Anti_Patterns.md`
   - [ ] Domain Bible for affected module(s)
   - [ ] `roadmap/Execution_Roadmap.md` — check if feature is already planned

2. **Clarify scope:**
   - Which module(s) are affected?
   - Is this a new API endpoint, frontend screen, or backend logic change?
   - Does it require DB migration?
   - Does it break existing API schema? (If yes → version as `/api/v2/`)

3. **Identify dependencies:**
   - Does `trading_engine` need data from another module? → call via `service.py`
   - Does frontend need new API? → implement backend first, then frontend
   - Does it need Redis cache? → follow `backend/04_Redis_Convention.md`

---

## Implementation Steps

### Step 1: Design (before coding)

Output a brief design doc:
```
Feature: [name]
Module: [domain]
Files to create: [...]
Files to modify: [...]
API changes: [new endpoints / schema changes]
DB changes: [yes/no — alembic migration needed?]
Cache strategy: [TTL, key pattern]
Tests to add: [...]
```

### Step 2: Backend (if applicable)

Order of implementation:
1. Service layer logic (`src/modules/{domain}/service.py`)
2. Pydantic request/response models
3. Route (`src/api/routes/`) — thin, delegates to service
4. Mount router in `main.py`
5. Tests (`tests/test_*.py`)

**Route template:**
```python
@router.get("/api/{resource}/{id}")
@limiter.limit("30/minute")
def get_resource(id: str, request: Request):
    return DomainService.get_resource(id)
```

### Step 3: Frontend (if applicable)

Order:
1. TypeScript interfaces in `lib/types.ts`
2. API client method in `lib/api.ts`
3. TanStack Query hook in `hooks/`
4. UI component
5. Page route in `app/`

### Step 4: Tests

Minimum tests for any new feature:
- [ ] Happy path
- [ ] 404 / validation error case
- [ ] Edge case relevant to domain (e.g., T→0 for pricing, missing ticker for credit)

### Step 5: Verification

```bash
pytest tests/ -v --tb=short
curl http://localhost:8008/docs  # verify new endpoint visible
# Smoke test 5 existing endpoints still work
```

---

## Feature Categories & Required Bibles

| Feature Type | Required Bibles |
|-------------|-----------------|
| New CW pricing logic | `quant/01_CW_Pricing`, `guardrails/Repository_Guardrails` |
| Credit / Merton / XGBoost | `quant/02_Credit_Risk`, `backend/03_Database_Convention` |
| Regime / HMM / GARCH | `quant/03_Regime_Analysis` |
| News / sentiment | `quant/04_News_Impact` |
| Trading / paper trader | `quant/05_Trading_Engine` |
| New API endpoint | `backend/02_API_Convention`, domain Bible |
| Frontend screen | `frontend/01_Frontend_Bible` |
| Redis / cache | `backend/04_Redis_Convention` |
| DB schema change | `backend/03_Database_Convention` |
| Auth / subscription | `roadmap/Execution_Roadmap` Phase 7 |
| Analyst prompt | `Analyst_Prompt.md`, `quant/01_CW_Pricing` |

---

## Output Format

When feature is complete, report:

```
## Feature: [name]

### Changes
- [file]: [what changed]

### API (if applicable)
- [METHOD] [endpoint] → [description]

### Tests
- [test file]: [N tests added, all passing]

### Verification
- [ ] pytest pass
- [ ] /docs updated
- [ ] No anti-patterns introduced
- [ ] Response schema documented
```

---

## Common Feature Requests & Specs

### Add new API endpoint
→ Follow `backend/02_API_Convention.md` thin route pattern  
→ Add to `system/02_Project_Index.md` API map

### Add caching to existing endpoint
→ TTL per `backend/04_Redis_Convention.md` key schema  
→ Graceful fallback if Redis down

### Add frontend page
→ Follow `frontend/01_Frontend_Bible.md` TanStack Query pattern  
→ Mobile responsive required

### Integrate new data source
→ Tag source in data (`source: "vietcap"|"ssi"|"vietstock"`)  
→ Never mix sources without normalization

### Add ML model inference
→ Load at startup in `src/api/state.py`  
→ Model file in `data/processed/` — version, don't overwrite  
→ Cache inference results (Redis TTL 15-30 min)

### Add subscription-gated feature
→ `require_vip()` dependency on route  
→ Frontend `<UpgradeBanner>` for free users  
→ See Phase 7 in `roadmap/Execution_Roadmap.md`

---

## Rejection Criteria (Do NOT implement if)

- Feature bypasses service layer (direct DB in route)
- Feature replaces Black-Scholes with pure ML output
- Feature has no test plan for financial logic changes
- Feature requires committing secrets
- Feature scope is unclear — ask user first
