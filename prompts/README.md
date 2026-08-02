# FINVISTA — Prompt Library

Thư viện prompt chuẩn cho AI Agent, Cursor, và developer làm việc trên repo Finvista.

**Cập nhật:** 26/06/2026  
**Repo:** `Finvista/` — Python 3.11+, FastAPI, SQLAlchemy, Next.js (planned)

---

## Cách dùng

### Session mới với AI Agent

1. Load **System Prompt** trước: [`system/01_System_Prompt.md`](system/01_System_Prompt.md)
2. Load **Guardrails**: [`guardrails/Repository_Guardrails.md`](guardrails/Repository_Guardrails.md)
3. Load **Bible** theo domain đang làm việc (xem bảng dưới)
4. Load **Task prompt** nếu có (`Bug_Fix.md`, `Feature_Request.md`, …)
5. Load **Roadmap** nếu làm theo phase: [`roadmap/Execution_Roadmap.md`](roadmap/Execution_Roadmap.md)

### Ví dụ prompt khởi động

```
Đọc và tuân thủ:
- prompts/system/01_System_Prompt.md
- prompts/guardrails/Repository_Guardrails.md
- prompts/quant/01_CW_Pricing.md
- prompts/roadmap/Execution_Roadmap.md (Section P0-1)

Thực hiện: Fix KalmanFilter bug trong regime API.
```

---

## Cấu trúc thư mục

```
prompts/
├── README.md                          ← Bạn đang đọc file này
├── system/                            ← Context toàn project
│   ├── 01_System_Prompt.md            ← Master system prompt (BẮT BUỘC)
│   ├── 02_Project_Index.md            ← File index + API map
│   └── 03_Architecture_Bible.md       ← Domain boundaries, data flow
├── guardrails/                        ← Rules không được vi phạm
│   ├── Repository_Guardrails.md
│   └── Anti_Patterns.md
├── backend/                           ← FastAPI, DB, Redis
│   ├── 01_Backend_Bible.md
│   ├── 02_API_Convention.md
│   ├── 03_Database_Convention.md
│   └── 04_Redis_Convention.md
├── frontend/                          ← Next.js SaaS UI
│   └── 01_Frontend_Bible.md
├── quant/                             ← Domain modules
│   ├── 01_CW_Pricing.md
│   ├── 02_Credit_Risk.md
│   ├── 03_Regime_Analysis.md
│   ├── 04_News_Impact.md
│   └── 05_Trading_Engine.md
├── devops/                            ← Test, CI/CD, Deploy
│   ├── 01_Testing.md
│   ├── 02_CICD.md
│   └── 03_Deployment.md
├── roadmap/
│   └── Execution_Roadmap.md           ← Phase 4.5 → 8, fixes, timeline
├── Analyst_Prompt.md                  ← CW end-user analysis template
├── Bug_Fix.md
├── Code_Review.md
├── Feature_Request.md
└── Refactor.md
```

---

## Map: Task → Prompt files

| Công việc | Prompt files cần load |
|-----------|----------------------|
| Fix bug backend | `01_System_Prompt`, `Repository_Guardrails`, `Bug_Fix`, domain Bible |
| Thêm API endpoint | `01_Backend_Bible`, `02_API_Convention`, domain Bible |
| CW pricing / Greeks | `01_CW_Pricing`, `Repository_Guardrails` |
| Credit / Merton / XGBoost | `02_Credit_Risk`, `03_Database_Convention` |
| Regime / HMM / GARCH | `03_Regime_Analysis` |
| News / sentiment / ML | `04_News_Impact` |
| Paper trader / AI Committee | `05_Trading_Engine` |
| Next.js frontend | `01_Frontend_Bible`, `02_Project_Index` (API map) |
| Redis cache | `04_Redis_Convention`, `03_Architecture_Bible` |
| PostgreSQL migrate | `03_Database_Convention`, `03_Deployment` |
| Viết tests | `01_Testing`, domain Bible |
| CI/CD / Docker | `02_CICD`, `03_Deployment` |
| Code review | `Code_Review`, `Repository_Guardrails`, `Anti_Patterns` |
| Refactor | `Refactor`, `Anti_Patterns`, domain Bible |
| CW analyst cho user | `Analyst_Prompt`, `01_CW_Pricing` |
| Roadmap / planning | `Execution_Roadmap`, `03_Architecture_Bible` |

---

## Trạng thái codebase (verified 26/06/2026)

| Thành phần | Trạng thái |
|------------|------------|
| Backend FastAPI (7 routers) | ✅ Production-ready |
| news_impact (service + 4 routes) | ✅ Hoàn chỉnh |
| regime routes (`/api/regime/*`) | ✅ Có — KalmanFilter bug cần fix |
| credit systemic (`SystemicRiskService`) | ✅ Có |
| Redis | ❌ Chỉ trong docs — chưa code |
| PostgreSQL production | ❌ SQLite default |
| Frontend Next.js | ❌ Chưa có |
| Tests | ⚠️ 1 file (`test_regime_portfolio.py`) |
| CI/CD | ❌ Chưa có `.github/workflows/` |

---

## Thứ tự ưu tiên hiện tại

1. **P0** — Fix bugs (KalmanFilter, …) → `Execution_Roadmap.md` Section 1
2. **Phase 5** — Next.js frontend → `01_Frontend_Bible.md`
3. **Phase 6** — Redis + PostgreSQL → `04_Redis_Convention.md`, `03_Deployment.md`
4. **Phase 7** — SaaS monetization
5. **Phase 8** — Docker, CI/CD, beta launch
