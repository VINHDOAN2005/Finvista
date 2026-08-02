# 🔌 Finvista API Documentation

## Base URL
- **Local**: `http://127.0.0.1:8008`
- **Production**: `https://your-backend-url.com`

## Authentication
Most endpoints require JWT authentication. Include the token in the Authorization header:
```
Authorization: Bearer <your-jwt-token>
```

---

## Health & Status

### GET `/`
**Description**: API overview and available endpoints

**Response**:
```json
{
  "gateway": "Finvista Quantitative Core REST API",
  "status": "online",
  "version": "1.0.0",
  "endpoints": {
    "interactive_docs": "/docs",
    "health_status": "/api/health",
    "corporate_credit_health": "/api/credit-health/{ticker}",
    "cw_opportunities": "/api/warrants/opportunities",
    "dynamic_greeks_calculator": "/api/warrants/greeks",
    "news_impact": "/api/news-impact/{ticker}",
    "news_ml_signal": "/api/news-impact/{ticker}/ml-signal",
    "market_regime": "/api/regime/market",
    "ticker_regime": "/api/regime/{ticker}"
  }
}
```

### GET `/api/health`
**Description**: System health check and model status

**Response**:
```json
{
  "status": "healthy",
  "model_registry": {
    "xgboost_model_loaded": true,
    "scaler_loaded": true
  },
  "database_layer": {
    "distress_dataset_found": true,
    "total_corporate_records": 1500
  },
  "live_market_cache": {
    "cached_warrants_present": true,
    "last_scan_timestamp": "2024-01-15T10:30:00Z"
  }
}
```

---

## Authentication

### POST `/api/auth/login`
**Description**: User login and JWT token generation

**Request Body**:
```json
{
  "username": "demo",
  "password": "finvista123"
}
```

**Response**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### POST `/api/auth/register`
**Description**: Register new user account

**Request Body**:
```json
{
  "username": "newuser",
  "password": "securepassword123"
}
```

**Response**:
```json
{
  "message": "User created successfully",
  "user_id": 123
}
```

---

## Covered Warrants

### GET `/api/warrants/opportunities`
**Description**: Get filtered CW opportunities with signals

**Query Parameters**:
- `strategy` (optional): `safe`, `balanced`, `aggressive` (default: `balanced`)
- `underlying` (optional): Filter by stock ticker
- `limit` (optional): Max results (default: 50)
- `vn30_only` (optional): Filter VN30 stocks only (default: false)

**Example**:
```
GET /api/warrants/opportunities?strategy=balanced&underlying=FPT&limit=20
```

**Response**:
```json
{
  "recommendations": [
    {
      "warrant_symbol": "FPT2510",
      "underlying_symbol": "FPT",
      "price": 2.5,
      "implied_volatility_pct": 35.2,
      "historical_volatility_pct": 28.1,
      "delta": 0.45,
      "gamma": 0.12,
      "theta_burn_day": -0.03,
      "vega": 0.08,
      "days_to_maturity": 45,
      "gearing": 2.3,
      "premium_pct": 12.5,
      "composite_g_score": 78.5,
      "recommendation_signal": "BUY",
      "underlying_altman_z": 4.2,
      "underlying_distress_prob": 0.02
    }
  ],
  "summary": {
    "total_analyzed": 150,
    "buy_signals": 45,
    "skip_signals": 105,
    "avg_g_score": 65.3
  }
}
```

### POST `/api/warrants/greeks`
**Description**: Calculate Greeks for custom CW parameters

**Request Body**:
```json
{
  "underlying_price": 85000,
  "strike_price": 82000,
  "time_to_maturity": 0.25,
  "risk_free_rate": 0.05,
  "volatility": 0.35,
  "option_type": "call"
}
```

**Response**:
```json
{
  "delta": 0.52,
  "gamma": 0.0001,
  "theta": -15.2,
  "vega": 120.5,
  "rho": 45.3,
  "theoretical_price": 3500,
  "intrinsic_value": 3000,
  "time_value": 500
}
```

### GET `/api/warrants/{symbol}/history`
**Description**: Get historical price data for specific CW

**Parameters**:
- `symbol`: CW ticker (e.g., `FPT2510`)
- `days` (optional): Lookback period (default: 30)

**Response**:
```json
{
  "symbol": "FPT2510",
  "historical_data": [
    {
      "date": "2024-01-01",
      "open": 2.3,
      "high": 2.5,
      "low": 2.2,
      "close": 2.4,
      "volume": 1000000
    }
  ],
  "statistics": {
    "avg_volatility_10d": 32.5,
    "avg_volatility_30d": 28.1,
    "max_drawdown": -15.2
  }
}
```

---

## Credit Health

### GET `/api/credit-health/{ticker}`
**Description**: Get comprehensive credit health analysis

**Parameters**:
- `ticker`: Stock ticker (e.g., `VNM`, `FPT`)

**Response**:
```json
{
  "ticker": "VNM",
  "altman_z_score": 3.8,
  "zone": "Safe",
  "distress_probability": 0.01,
  "merton_distance_to_default": 4.2,
  "merton_pd": 0.005,
  "industry_adjusted_roaa": 5.2,
  "industry_percentile": 75,
  "current_ratio": 1.8,
  "debt_to_equity": 0.4,
  "key_ratios": {
    "roa": 8.5,
    "roe": 15.2,
    "operating_margin": 12.3,
    "interest_coverage": 8.5
  },
  "recommendation": "LOW_RISK"
}
```

### GET `/api/credit-health/scan`
**Description**: Batch scan multiple tickers

**Query Parameters**:
- `tickers`: Comma-separated list (e.g., `VNM,FPT,HPG`)

**Response**:
```json
{
  "results": [
    {
      "ticker": "VNM",
      "altman_z_score": 3.8,
      "zone": "Safe"
    },
    {
      "ticker": "FPT",
      "altman_z_score": 4.2,
      "zone": "Safe"
    }
  ],
  "summary": {
    "safe": 2,
    "grey": 0,
    "distress": 0
  }
}
```

---

## Portfolio & Paper Trading

### GET `/api/portfolio`
**Description**: Get current portfolio status

**Response**:
```json
{
  "cash": 85000000,
  "initial_cash": 100000000,
  "total_nav": 123000000,
  "cumulative_p_l_vnd": 23000000,
  "cumulative_p_l_pct": 23.0,
  "positions_value": 38000000,
  "active_positions": [
    {
      "symbol": "FPT2510",
      "underlying": "FPT",
      "qty": 1000,
      "buy_price": 2.3,
      "current_price": 2.8,
      "current_value": 2800000,
      "p_l_vnd": 500000,
      "p_l_pct": 21.7,
      "is_locked": false,
      "days_held": 15
    }
  ],
  "history": [
    {
      "date": "2024-01-15",
      "nav": 123000000,
      "cash": 85000000,
      "positions_value": 38000000
    }
  ]
}
```

### POST `/api/portfolio/order`
**Description**: Place buy/sell order

**Request Body**:
```json
{
  "symbol": "FPT2510",
  "side": "BUY",
  "qty": 1000,
  "price": 2.5,
  "reason": "Volatility arbitrage setup"
}
```

**Response**:
```json
{
  "message": "Order executed successfully",
  "order_id": 12345,
  "executed_price": 2.5,
  "executed_qty": 1000,
  "total_value": 2500000,
  "fee": 1250,
  "new_portfolio_value": 120487500
}
```

### POST `/api/portfolio/reset`
**Description**: Reset portfolio to initial state

**Response**:
```json
{
  "message": "Portfolio reset successfully",
  "new_cash": 100000000,
  "new_nav": 100000000
}
```

### POST `/api/portfolio/scan`
**Description**: Run risk scan and auto-rebalance

**Query Parameters**:
- `force` (optional): Force scan regardless of schedule

**Response**:
```json
{
  "message": "Risk scan completed",
  "actions_executed": [
    "SELL FPT2510 - Take profit triggered",
    "BUY HPG2510 - New opportunity"
  ],
  "risk_summary": {
    "positions_analyzed": 5,
    "risk_alerts": 1,
    "rebalancing_actions": 2
  }
}
```

---

## Market Regime Analysis

### GET `/api/regime/market`
**Description**: Get overall market regime analysis

**Response**:
```json
{
  "current_regime": "BULLISH",
  "confidence": 0.85,
  "volatility_regime": "LOW",
  "trend_strength": 0.72,
  "indicators": {
    "hmm_state": 1,
    "garch_volatility": 0.18,
    "kalman_trend": 0.05,
    "ema_alignment": "BULLISH"
  },
  "forecast": {
    "regime_probability": {
      "bullish": 0.70,
      "bearish": 0.15,
      "sideways": 0.15
    },
    "expected_volatility": 0.20
  }
}
```

### GET `/api/regime/{ticker}`
**Description**: Get regime analysis for specific ticker

**Parameters**:
- `ticker`: Stock ticker

**Response**:
```json
{
  "ticker": "FPT",
  "current_regime": "BULLISH",
  "regime_history": [
    {
      "date": "2024-01-01",
      "regime": "BULLISH",
      "probability": 0.82
    }
  ],
  "volatility_analysis": {
    "current_vol": 0.25,
    "historical_avg": 0.28,
    "vol_regime": "NORMAL"
  }
}
```

---

## News Impact Analysis

### GET `/api/news-impact/{ticker}`
**Description**: Get news impact analysis for ticker

**Parameters**:
- `ticker`: Stock ticker
- `days` (optional): Lookback period (default: 30)

**Response**:
```json
{
  "ticker": "VNM",
  "news_events": [
    {
      "date": "2024-01-10",
      "title": "VNM announces quarterly results",
      "sentiment": "POSITIVE",
      "impact_score": 0.75,
      "price_change_1d": 2.5,
      "price_change_3d": 3.2,
      "price_change_5d": 1.8
    }
  ],
  "summary": {
    "total_events": 5,
    "positive_events": 3,
    "negative_events": 1,
    "neutral_events": 1,
    "avg_price_impact_3d": 1.5
  }
}
```

### GET `/api/news-impact/{ticker}/ml-signal`
**Description**: Get ML-based news trading signal

**Parameters**:
- `ticker`: Stock ticker

**Response**:
```json
{
  "ticker": "VNM",
  "ml_signal": "BUY",
  "confidence": 0.78,
  "feature_importance": {
    "sentiment_score": 0.35,
    "event_type": 0.25,
    "market_regime": 0.20,
    "historical_impact": 0.20
  },
  "expected_move": {
    "direction": "UP",
    "magnitude_pct": 2.5,
    "time_horizon_days": 5
  }
}
```

---

## AI Chat & Analysis

### POST `/api/chat/completions`
**Description**: Get AI-powered market analysis

**Request Body**:
```json
{
  "messages": [
    {
      "role": "user",
      "content": "Analyze FPT2510 covered warrant"
    }
  ],
  "context": {
    "symbol": "FPT2510",
    "current_price": 2.5,
    "market_regime": "BULLISH"
  }
}
```

**Response**:
```json
{
  "response": "Based on current analysis, FPT2510 shows strong BUY signal...",
  "reasoning": "High G-score of 78.5, positive IV/HV ratio...",
  "recommendation": "BUY",
  "confidence": 0.82
}
```

---

## Market Data

### GET `/api/market/overview`
**Description**: Get overall market overview

**Response**:
```json
{
  "vn_index": {
    "value": 1250.5,
    "change": 15.2,
    "change_pct": 1.23
  },
  "market_sentiment": "BULLISH",
  "sector_performance": [
    {
      "sector": "Technology",
      "change_pct": 2.5
    },
    {
      "sector": "Banking",
      "change_pct": 1.8
    }
  ],
  "top_movers": [
    {
      "ticker": "FPT",
      "change_pct": 3.2
    }
  ]
}
```

---

## Error Responses

All endpoints may return error responses:

```json
{
  "status": "error",
  "error_code": "ERROR_CODE",
  "message": "Human-readable error message",
  "details": {}
}
```

### Common Error Codes
- `UNAUTHORIZED`: Invalid or missing authentication
- `RATE_LIMIT_EXCEEDED`: Too many requests
- `INVALID_INPUT`: Malformed request parameters
- `RESOURCE_NOT_FOUND`: Requested resource doesn't exist
- `INTERNAL_ERROR`: Server-side error

---

## Rate Limiting

- **Default**: 100 requests per minute
- **Burst**: 10 requests per second
- **Headers**:
  - `X-RateLimit-Limit`: Request limit
  - `X-RateLimit-Remaining`: Remaining requests
  - `X-RateLimit-Reset`: Reset timestamp

---

## WebSocket

### Connect to `/api/ws`
**Description**: Real-time market data updates

**Message Format**:
```json
{
  "type": "subscribe",
  "channels": ["market_data", "portfolio_updates"]
}
```

**Server Response**:
```json
{
  "type": "market_update",
  "data": {
    "symbol": "FPT2510",
    "price": 2.55,
    "change": 0.05,
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

---

## SDK & Libraries

### Python
```python
import requests

# Example: Get CW opportunities
response = requests.get(
    "http://127.0.0.1:8008/api/warrants/opportunities",
    params={"strategy": "balanced", "limit": 20},
    headers={"Authorization": f"Bearer {token}"}
)
data = response.json()
```

### JavaScript
```javascript
// Example: Get credit health
const response = await fetch(
  'http://127.0.0.1:8008/api/credit-health/VNM',
  {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    }
  }
);
const data = await response.json();
```

---

## Testing

### Interactive Documentation
Visit `/docs` for interactive Swagger UI

### Example cURL Commands
```bash
# Health check
curl http://127.0.0.1:8008/api/health

# Get CW opportunities
curl "http://127.0.0.1:8008/api/warrants/opportunities?strategy=balanced"

# Login
curl -X POST http://127.0.0.1:8008/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"demo","password":"finvista123"}'
```
