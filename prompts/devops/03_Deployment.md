# 03. DEPLOYMENT & PRODUCTION BIBLE
**Domain:** Infrastructure, Docker, Cloud, Monitoring  
**Target:** Beta launch 100 users — Week 8

---

## 1. Production Architecture

```
                    [Cloudflare DNS + DDoS]
                              │
              ┌───────────────┴───────────────┐
              │                               │
      [Vercel Edge CDN]              [VPS Ubuntu 22.04]
      finvista.vn                    4 vCPU / 8GB RAM
      Next.js Frontend                      │
                                    [Nginx Reverse Proxy]
                                    SSL (Let's Encrypt)
                                           │
                              ┌────────────┼────────────┐
                              │            │            │
                        [FastAPI]    [PostgreSQL]  [Redis 7]
                        :8008         :5432         :6379
                              │
                        [Celery Worker + Beat]
```

**Domains:**
- `finvista.vn` → Vercel (frontend)
- `api.finvista.vn` → VPS (backend)
- `ws.finvista.vn` → VPS WebSocket (nginx upgrade)

---

## 2. Docker Compose

### 2.1 Development (`docker-compose.yml`)

```yaml
version: "3.9"

services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8008:8008"
    env_file: .env
    volumes:
      - ./data:/app/data
    depends_on:
      db:
        condition: service_healthy
      cache:
        condition: service_started
    command: uvicorn src.api.main:app --host 0.0.0.0 --port 8008 --reload

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      NEXT_PUBLIC_API_URL: http://backend:8008
      NEXT_PUBLIC_WS_URL: ws://backend:8008/api/ws
    depends_on:
      - backend

  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: finvista
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: finvista
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U finvista"]
      interval: 5s
      timeout: 5s
      retries: 5

  cache:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redisdata:/data
    command: redis-server --appendonly yes

  worker:
    build:
      context: .
      dockerfile: Dockerfile
    env_file: .env
    depends_on:
      - db
      - cache
    command: celery -A src.worker worker --beat --loglevel=info

volumes:
  pgdata:
  redisdata:
```

### 2.2 Backend Dockerfile

```dockerfile
# Dockerfile
FROM python:3.11-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
RUN useradd -m -u 1000 finvista_user
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY . .
RUN chown -R finvista_user:finvista_user /app
USER finvista_user
EXPOSE 8008
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8008"]
```

### 2.3 Frontend Dockerfile

```dockerfile
# frontend/Dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-alpine
WORKDIR /app
RUN adduser -D finvista
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
USER finvista
EXPOSE 3000
CMD ["node", "server.js"]
```

---

## 3. Environment Variables (Production)

```env
# .env.production (NEVER commit)

# Database
DATABASE_URL=postgresql://finvista:STRONG_PASSWORD@db:5432/finvista

# Redis
REDIS_URL=redis://cache:6379/0
REDIS_ENABLED=true

# Auth
JWT_SECRET=generate-256-bit-random-string
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440

# AI
GEMINI_API_KEY=...

# Telegram
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...

# PayOS (Phase 7)
PAYOS_CLIENT_ID=...
PAYOS_API_KEY=...
PAYOS_CHECKSUM_KEY=...

# App
ENVIRONMENT=production
CORS_ORIGINS=https://finvista.vn,https://www.finvista.vn
```

**Validation:** App MUST crash on startup if required vars missing (`pydantic-settings` in `src/core/config.py`).

---

## 4. Nginx Configuration

```nginx
# /etc/nginx/sites-available/finvista

upstream fastapi {
    server 127.0.0.1:8008;
}

server {
    listen 443 ssl http2;
    server_name api.finvista.vn;

    ssl_certificate /etc/letsencrypt/live/api.finvista.vn/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.finvista.vn/privkey.pem;

    location / {
        proxy_pass http://fastapi;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 60s;
    }

    location /api/ws {
        proxy_pass http://fastapi;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400s;
    }
}
```

**SSL:** `certbot --nginx -d api.finvista.vn`

---

## 5. Database Migration (SQLite → PostgreSQL)

**Script:** `scripts/maintenance/migrate_sqlite_to_postgres.py`

Steps:
1. Export SQLite tables to CSV/JSON
2. Create PostgreSQL schema via `alembic upgrade head`
3. Import data with type conversion
4. Verify row counts match
5. Switch `DATABASE_URL` in production `.env`
6. Run full pytest suite against PostgreSQL

**Fix in `database.py` for PostgreSQL:**
```python
connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_size=10,
    max_overflow=20,
)
```

---

## 6. Health Checks & Startup Validation

```python
# src/api/main.py
@app.get("/health")
def health_check():
    from src.infra.redis_client import get_redis
    from src.core.database import engine
    
    db_ok = False
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass
    
    return {
        "status": "ok" if db_ok else "degraded",
        "database": "ok" if db_ok else "error",
        "redis": get_redis().health_check(),
        "version": "1.0.0",
    }
```

**Docker healthcheck:**
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8008/health"]
  interval: 30s
  timeout: 10s
  retries: 3
```

**Startup script:** `scripts/maintenance/health_check_connectivity.py` — run before deploy.

---

## 7. Load Testing

**Tool:** Locust  
**File:** `scripts/maintenance/locustfile.py`

```python
from locust import HttpUser, task, between

class FinvistaUser(HttpUser):
    wait_time = between(1, 3)
    host = "https://api.finvista.vn"

    @task(5)
    def warrants_opportunities(self):
        self.client.get("/api/warrants/opportunities")

    @task(2)
    def credit_health(self):
        self.client.get("/api/credit-health/VNM")

    @task(2)
    def regime_market(self):
        self.client.get("/api/regime/market")

    @task(1)
    def news_sentiment(self):
        self.client.get("/api/news-impact/VNM/sentiment")
```

**Targets:**
- 5,000 concurrent users
- 100 requests/second sustained
- p95 latency < 500ms on `/api/warrants/opportunities`
- 0% error rate under normal load

**Tuning if fail:**
- Redis cache hit rate > 80% for CW prices
- PostgreSQL connection pool size increase
- Uvicorn workers: `--workers 4`

---

## 8. Monitoring (Optional but Recommended)

| Tool | Purpose |
|------|---------|
| Grafana + Prometheus | API latency, error rate, Redis hit rate |
| Sentry | Python + Next.js exception tracking |
| Vercel Analytics | Frontend Web Vitals |
| UptimeRobot | `/health` endpoint ping every 5 min |

---

## 9. Deploy Checklist (Go-Live)

### Pre-deploy
- [ ] All pytest pass (15+ tests)
- [ ] `DATABASE_URL` points to PostgreSQL
- [ ] Redis running with fallback tested
- [ ] `.env` secrets set on VPS (not in git)
- [ ] `alembic upgrade head` applied
- [ ] SSL certificates valid
- [ ] CORS restricted to production domain
- [ ] Rate limits configured for production traffic

### Deploy steps
```bash
# VPS
git pull origin main
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
docker compose exec backend alembic upgrade head

# Vercel
cd frontend && vercel --prod
```

### Post-deploy smoke test
```bash
curl https://api.finvista.vn/health
curl https://api.finvista.vn/api/regime/market
curl https://api.finvista.vn/api/warrants/opportunities | head -c 200
```

### Beta launch
- [ ] Invite 100 users (brokers + VIP investors)
- [ ] Monitor error rate first 48 hours
- [ ] Telegram alert channel for system errors

---

## 10. Rollback Plan

```bash
# Rollback backend
docker compose -f docker-compose.prod.yml down
git checkout <previous-tag>
docker compose -f docker-compose.prod.yml up -d

# Rollback frontend
vercel rollback
```

Keep last 3 Docker images tagged by git SHA.

---

## 11. Security Hardening (Production)

- [ ] Firewall: only 80, 443, 22 open on VPS
- [ ] PostgreSQL + Redis: internal network only, not exposed publicly
- [ ] JWT secret: 256-bit random, rotated quarterly
- [ ] Rate limiting: SlowAPI enabled on all public endpoints
- [ ] PayOS webhook: verify checksum signature
- [ ] No `allow_origins=["*"]` in production CORS
