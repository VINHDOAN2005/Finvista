# 02. CI/CD & DEPLOYMENT BIBLE
**Domain:** Infrastructure & GitHub Actions
**Stack:** Docker, GitHub Actions, Ubuntu VPS

## 1. CI Pipeline (Continuous Integration)
Every Pull Request to the `main` or `develop` branch MUST pass the following automated checks before merging:
1. **Linting & Formatting:** Use `Ruff` for blazing-fast linting. No `flake8` or `black` to avoid dependency bloat.
2. **Type Checking:** Run `mypy . --strict`. The build fails if type hints are missing or invalid.
3. **Unit & Integration Tests:** Run `pytest tests/` with coverage. Minimum coverage threshold is 85% for `/modules`.
4. **Security Scan:** Run `bandit` to check for hardcoded secrets or SQL injection vulnerabilities.

## 2. Docker & Containerization Rules
* **Multi-stage Builds:** The `Dockerfile` must use multi-stage builds to keep the final image size under 500MB (excluding PyTorch/ML artifacts, which should be mounted via volumes).
* **Base Image:** Use `python:3.11-slim` or `3.12-slim`. NEVER use the full `python:3.x` image or `alpine` (Alpine causes C-extension compilation issues for Pandas and Numpy).
* **Permissions:** Do not run the FastAPI application as `root`. Create a dedicated `finvista_user` in the Dockerfile.

## 3. Environment Variables
* Never commit `.env` files.
* CI/CD pipelines must inject variables via GitHub Secrets.
* Variables must be strictly validated at startup using `pydantic-settings` in `src/core/config.py`. If a variable like `POSTGRES_URL` is missing, the app MUST crash immediately on startup, not fail silently later.

---

## 4. GitHub Actions Workflows (TO CREATE — Phase 8)

### 4.1 CI Pipeline (`.github/workflows/ci.yml`)

```yaml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15-alpine
        env:
          POSTGRES_USER: finvista
          POSTGRES_PASSWORD: testpassword
          POSTGRES_DB: finvista_test
        ports: ["5432:5432"]
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      redis:
        image: redis:7-alpine
        ports: ["6379:6379"]

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: pip

      - name: Install dependencies
        run: pip install -r requirements.txt ruff pytest pytest-cov fakeredis

      - name: Lint with Ruff
        run: ruff check src/ tests/

      - name: Run tests
        env:
          DATABASE_URL: postgresql://finvista:testpassword@localhost:5432/finvista_test
          REDIS_URL: redis://localhost:6379/0
          JWT_SECRET: test-secret-for-ci-only
        run: pytest tests/ -v --tb=short

      - name: Build Docker image
        run: docker build -t finvista-backend:${{ github.sha }} .
```

### 4.2 Deploy Pipeline (`.github/workflows/deploy.yml`)

```yaml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4

      - name: Deploy to VPS via SSH
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.VPS_HOST }}
          username: ${{ secrets.VPS_USER }}
          key: ${{ secrets.VPS_SSH_KEY }}
          script: |
            cd /opt/finvista
            git pull origin main
            docker compose -f docker-compose.prod.yml build
            docker compose -f docker-compose.prod.yml up -d
            docker compose exec -T backend alembic upgrade head
            curl -f http://localhost:8008/health
```

---

## 5. Branch Strategy

| Branch | Purpose | CI | Deploy |
|--------|---------|-----|--------|
| `main` | Production | ✅ Full | ✅ VPS |
| `develop` | Integration | ✅ Full | ❌ |
| `feature/*` | Feature work | ✅ on PR | ❌ |

---

## 6. Pre-commit Recommendations (Optional)

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.4
    hooks:
      - id: ruff
      - id: ruff-format
```

---

## 7. CI Gate Criteria (Phase 8)

PR cannot merge unless:
- [ ] `ruff check` passes
- [ ] `pytest tests/ -v` passes (15+ tests)
- [ ] Docker build succeeds
- [ ] No secrets detected by `bandit`
- [ ] Coverage ≥ 85% for `src/modules/` (stretch goal)