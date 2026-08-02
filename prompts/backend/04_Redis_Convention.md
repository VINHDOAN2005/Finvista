# 04. REDIS CACHE CONVENTION
**Status:** PLANNED — Phase 6 (not yet implemented)  
**Current fallback:** `src/infra/market_cache.py` (JSON file) + in-memory dict caches

---

## 1. Why Redis

FINVISTA needs sub-15-second TTL caching for:
- Live CW bid/ask/last prices during HOSE session (9:00–15:00)
- Real-time Greeks (Δ, Γ, Θ, ν, ρ) per CW symbol
- Daily HV cache per underlying (refresh 16:00)
- Credit health results (TTL 30 min)
- Regime market state (TTL 1 hour)
- Systemic network graph (TTL 30 min — currently in-memory)

JSON file cache cannot scale to WebSocket fan-out + 5000 concurrent users.

---

## 2. Implementation Spec

### 2.1 Client Wrapper

**File to create:** `src/infra/redis_client.py`

```python
import json
import redis
from typing import Any, Optional
from src.core.utils import logger

class RedisCache:
    """Redis wrapper with graceful fallback to None on connection failure."""

    def __init__(self, url: str = "redis://localhost:6379/0"):
        self._available = False
        try:
            self.client = redis.from_url(url, decode_responses=True, socket_timeout=2)
            self.client.ping()
            self._available = True
            logger.info("✅ Redis connected")
        except Exception as e:
            logger.warning(f"⚠️ Redis unavailable, using fallback: {e}")
            self.client = None

    @property
    def available(self) -> bool:
        return self._available

    def set_json(self, key: str, value: Any, ttl: int = 15) -> bool:
        if not self.client:
            return False
        try:
            self.client.setex(key, ttl, json.dumps(value, default=str))
            return True
        except Exception as e:
            logger.debug(f"Redis set failed [{key}]: {e}")
            return False

    def get_json(self, key: str) -> Optional[Any]:
        if not self.client:
            return None
        try:
            raw = self.client.get(key)
            return json.loads(raw) if raw else None
        except Exception as e:
            logger.debug(f"Redis get failed [{key}]: {e}")
            return None

    def delete(self, key: str) -> None:
        if self.client:
            self.client.delete(key)

    def health_check(self) -> dict:
        if not self.client:
            return {"status": "unavailable", "fallback": "json_cache"}
        try:
            self.client.ping()
            return {"status": "ok", "fallback": None}
        except Exception as e:
            return {"status": "error", "message": str(e), "fallback": "json_cache"}


# Singleton
_redis: Optional[RedisCache] = None

def get_redis() -> RedisCache:
    global _redis
    if _redis is None:
        from src.core.config import settings
        _redis = RedisCache(url=getattr(settings, "REDIS_URL", "redis://localhost:6379/0"))
    return _redis
```

### 2.2 Graceful Degradation Rule

**MANDATORY:** If Redis is down, app MUST continue running.

Fallback chain:
```
Redis hit → return cached
Redis miss/down → JSON file cache (market_cache.py)
JSON miss → compute fresh → write to both Redis + JSON
```

Never raise unhandled exception from cache layer.

---

## 3. Key Schema

| Key Pattern | TTL | Value Type | Written By | Read By |
|-------------|-----|------------|------------|---------|
| `cw:live_price:{symbol}` | 15s | `{bid, ask, last, pct_change, ts}` | vietcap_scraper / orderbook_scraper | cw_pricing/service, WebSocket |
| `cw:greeks:{symbol}` | 15s | `{delta, gamma, theta, vega, rho, iv}` | cw_pricing/service | warrants routes, WebSocket |
| `underlying:hv:{ticker}` | 86400s | `{hv_20d, hv_60d, computed_at}` | scheduler (16:00 daily) | cw_pricing, analyst prompt |
| `credit:health:{ticker}` | 1800s | Full credit health dict | credit_risk/service | credit routes |
| `regime:market` | 3600s | HMM state dict | regime_analysis | regime routes |
| `systemic:network` | 1800s | Network summary dict | systemic_service | credit routes |
| `news:sentiment:{ticker}` | 900s | Sentiment score dict | news_impact/service | news_impact routes |
| `news:ml_signal:{ticker}` | 1800s | ML signal dict | news_impact/service | ai_committee |

**Key naming rules:**
- Lowercase, colon-separated namespaces
- No spaces, no special chars except `:`
- Ticker/symbol always UPPERCASE in key: `cw:greeks:CWG1234`

---

## 4. Migration Plan (Phase 6.1)

### Step 1: Add dependency
```
# requirements.txt
redis>=5.0.0
```

### Step 2: Config
```python
# src/core/config.py
REDIS_URL: str = "redis://localhost:6379/0"
REDIS_ENABLED: bool = True
```

### Step 3: Refactor existing caches

| Current | Target |
|---------|--------|
| `market_cache.py` JSON file | Redis primary, JSON fallback |
| `NewsImpactService._cache` dict | `get_redis().set_json("news:...")` |
| `SystemicRiskService._cache` dict | `get_redis().set_json("systemic:network")` |
| `CreditRiskService` (no cache) | Add `credit:health:{ticker}` |

### Step 4: Health endpoint
```python
# src/api/main.py
@app.get("/health")
def health():
    return {
        "status": "ok",
        "redis": get_redis().health_check(),
        "database": "ok",  # add DB ping
    }
```

---

## 5. Pub/Sub for WebSocket (Phase 5.4 + 6.1)

When CW price updates in Redis, publish to channel:

```python
# Writer (scraper)
redis.client.publish("cw:updates", json.dumps({"symbol": "CWG1234", "price": 1250}))

# Reader (WebSocket handler)
pubsub = redis.client.pubsub()
pubsub.subscribe("cw:updates")
for message in pubsub.listen():
    await websocket.send_json(json.loads(message["data"]))
```

Channels:
- `cw:updates` — price/Greeks changes
- `signals:alerts` — AI Committee new signals
- `regime:changes` — HMM state transitions

---

## 6. Cache Invalidation Rules

| Event | Action |
|-------|--------|
| Market open (09:00) | Delete all `cw:live_price:*` and `cw:greeks:*` |
| Significant news (news_impact pipeline) | Delete `news:sentiment:{ticker}` for affected tickers |
| Model retrain | Delete all `news:ml_signal:*` |
| Manual admin flush | `redis-cli FLUSHDB` (dev only) |

Scheduled invalidation via Celery Beat (Phase 6) or APScheduler.

---

## 7. Testing Redis Layer

```python
# tests/test_redis_client.py
def test_redis_fallback_when_unavailable():
    cache = RedisCache(url="redis://invalid:9999/0")
    assert cache.available is False
    assert cache.get_json("any:key") is None  # no exception

def test_set_get_json(mock_redis):
    cache = RedisCache()
    cache.set_json("test:key", {"a": 1}, ttl=60)
    assert cache.get_json("test:key") == {"a": 1}
```

Use `fakeredis` for unit tests — never require live Redis in CI.

---

## 8. Docker (Phase 8)

```yaml
# docker-compose.yml
cache:
  image: redis:7-alpine
  ports: ["6379:6379"]
  volumes: [redisdata:/data]
  command: redis-server --appendonly yes
```

Backend env: `REDIS_URL=redis://cache:6379/0`

---

## 9. Anti-Patterns (NEVER)

- ❌ Store user passwords or JWT tokens in Redis without encryption
- ❌ Use Redis as primary database (PostgreSQL is source of truth)
- ❌ TTL > 24h for live price data
- ❌ Block API response waiting for Redis if Redis is slow — timeout 2s max
- ❌ Cache ML model objects in Redis (use joblib file + in-memory singleton)
