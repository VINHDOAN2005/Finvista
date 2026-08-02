# 🚀 Finvista Deployment Guide

## Phase 1: Supabase Setup

### 1.1 Tạo Supabase Project
1. Truy cập https://supabase.com
2. Sign up/Login → Create new project
3. Project name: `finvista-prod`
4. Database password: (lưu lại password này)
5. Region: Singapore (gần Việt Nam nhất)
6. Wait for project to be ready (~2-3 phút)

### 1.2 Lấy Database Connection String
1. Vào project → Settings → Database
2. Copy connection string URI:
   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
   ```
3. Thêm vào file `.env`:
   ```bash
   DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
   ```

### 1.3 Setup Database Schema
```bash
# Cài đặt Supabase CLI (nếu chưa có)
npm install -g supabase

# Hoặc dùng trực qua Supabase Dashboard SQL Editor
# Vào SQL Editor trong Supabase Dashboard và chạy script sau:
```

**SQL Schema Script** (copy vào Supabase SQL Editor):
```sql
-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR UNIQUE NOT NULL,
    hashed_password VARCHAR NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Portfolios table
CREATE TABLE portfolios (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    cash FLOAT DEFAULT 100000000.0,
    initial_cash FLOAT DEFAULT 100000000.0
);

-- Positions table
CREATE TABLE positions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    symbol VARCHAR NOT NULL,
    underlying VARCHAR,
    qty INTEGER NOT NULL,
    buy_price FLOAT NOT NULL,
    buy_date VARCHAR NOT NULL,
    settlement_date VARCHAR NOT NULL,
    total_cost FLOAT NOT NULL,
    score_at_buy FLOAT,
    days_at_buy INTEGER
);

CREATE INDEX ix_positions_user_id ON positions(user_id);
CREATE INDEX ix_positions_symbol ON positions(symbol);

-- Transaction history
CREATE TABLE transaction_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    symbol VARCHAR NOT NULL,
    underlying VARCHAR,
    type VARCHAR NOT NULL,
    qty INTEGER NOT NULL,
    price FLOAT NOT NULL,
    value FLOAT NOT NULL,
    fee FLOAT NOT NULL,
    date VARCHAR NOT NULL,
    reason VARCHAR
);

CREATE INDEX ix_transaction_history_user_id ON transaction_history(user_id);
CREATE INDEX ix_transaction_history_symbol ON transaction_history(symbol);

-- Portfolio NAV history
CREATE TABLE portfolio_nav_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    total_nav FLOAT NOT NULL,
    cash FLOAT NOT NULL,
    positions_value FLOAT NOT NULL,
    date VARCHAR NOT NULL
);

CREATE INDEX ix_portfolio_nav_history_user_id ON portfolio_nav_history(user_id);

-- Market opportunities
CREATE TABLE market_opportunities (
    symbol VARCHAR PRIMARY KEY,
    underlying VARCHAR,
    issuer VARCHAR,
    price FLOAT,
    price_change_pct FLOAT,
    intrinsic_value FLOAT,
    break_even_price FLOAT,
    premium_pct FLOAT,
    risk_monthly_pct FLOAT,
    gearing FLOAT,
    days_to_maturity INTEGER,
    score FLOAT,
    decision_signal VARCHAR,
    underlying_price FLOAT,
    ratio VARCHAR,
    strike_price FLOAT,
    volume FLOAT,
    turnover FLOAT,
    implied_volatility_pct FLOAT,
    historical_volatility_pct FLOAT,
    delta FLOAT,
    gamma FLOAT,
    theta_burn_day FLOAT,
    vega FLOAT,
    prob_itm FLOAT,
    theoretical_price FLOAT,
    upside_pct FLOAT,
    garch_theoretical_price FLOAT,
    garch_upside_pct FLOAT,
    merton_theoretical_price FLOAT,
    merton_upside_pct FLOAT,
    proj_3d_flat_pct FLOAT,
    proj_3d_up_pct FLOAT,
    proj_3d_down_pct FLOAT,
    moneyness_category VARCHAR,
    underlying_distress_prob FLOAT,
    underlying_is_distressed INTEGER,
    underlying_altman_z FLOAT,
    underlying_systemic_prob FLOAT,
    underlying_systemic_delta FLOAT,
    underlying_systemic_is_distressed INTEGER,
    underlying_nim FLOAT,
    underlying_npl FLOAT,
    underlying_casa FLOAT,
    underlying_car FLOAT,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX ix_market_opportunities_underlying ON market_opportunities(underlying);
CREATE INDEX ix_market_opportunities_days_to_maturity ON market_opportunities(days_to_maturity);
CREATE INDEX ix_market_opportunities_score ON market_opportunities(score);

-- CW historical prices
CREATE TABLE cw_history (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR NOT NULL,
    date VARCHAR NOT NULL,
    open FLOAT,
    high FLOAT,
    low FLOAT,
    close FLOAT,
    volume FLOAT,
    ref_price FLOAT
);

CREATE INDEX ix_cw_history_symbol ON cw_history(symbol);
CREATE INDEX ix_cw_history_date ON cw_history(date);

-- Stock historical prices
CREATE TABLE stock_history (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR NOT NULL,
    date VARCHAR NOT NULL,
    open FLOAT,
    high FLOAT,
    low FLOAT,
    close FLOAT,
    volume FLOAT,
    ref_price FLOAT
);

CREATE INDEX ix_stock_history_symbol ON stock_history(symbol);
CREATE INDEX ix_stock_history_date ON stock_history(date);

-- AI analysis memory
CREATE TABLE ai_analysis_memory (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR NOT NULL,
    underlying VARCHAR,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    decision VARCHAR,
    consensus_score FLOAT,
    rationale_summary VARCHAR,
    price_at_analysis FLOAT,
    underlying_price_at_analysis FLOAT,
    iv_at_analysis FLOAT,
    delta_at_analysis FLOAT,
    days_to_maturity INTEGER,
    is_correct BOOLEAN,
    max_upside_pct FLOAT,
    result_commentary VARCHAR
);

CREATE INDEX ix_ai_analysis_memory_symbol ON ai_analysis_memory(symbol);
CREATE INDEX ix_ai_analysis_memory_underlying ON ai_analysis_memory(underlying);

-- Corporate news
CREATE TABLE corporate_news (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR NOT NULL,
    title VARCHAR NOT NULL,
    link VARCHAR UNIQUE NOT NULL,
    date VARCHAR,
    source VARCHAR DEFAULT 'Vietstock',
    summary VARCHAR,
    category VARCHAR,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX ix_corporate_news_symbol ON corporate_news(symbol);

-- Corporate events
CREATE TABLE corporate_events (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR NOT NULL,
    event_date VARCHAR,
    event_type VARCHAR,
    description VARCHAR,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX ix_corporate_events_ticker ON corporate_events(ticker);
CREATE INDEX ix_corporate_events_event_date ON corporate_events(event_date);

-- Company distress analysis
CREATE TABLE company_distress_analysis (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR NOT NULL,
    year INTEGER NOT NULL,
    industry VARCHAR,
    roaa FLOAT,
    roae FLOAT,
    industry_adjusted_roaa FLOAT,
    industry_roaa_percentile FLOAT,
    industry_adjusted_roae FLOAT,
    industry_roae_percentile FLOAT,
    industry_adjusted_debt_ratio FLOAT,
    industry_debt_ratio_percentile FLOAT,
    current_ratio FLOAT,
    working_capital FLOAT,
    working_capital_to_assets FLOAT,
    ocf_to_current_liabilities FLOAT,
    cash_ratio FLOAT,
    ocf_to_total_debt FLOAT,
    cfo_interest_coverage FLOAT,
    roa FLOAT,
    roe FLOAT,
    operating_margin FLOAT,
    ebit_to_assets FLOAT,
    ocf_to_pat FLOAT,
    equity_multiplier FLOAT,
    ebit_to_interest FLOAT,
    icr FLOAT,
    debt_to_equity FLOAT,
    debt_ratio FLOAT,
    company_size FLOAT,
    revenue_growth FLOAT,
    assets_growth FLOAT,
    altman_x1 FLOAT,
    altman_x2 FLOAT,
    altman_x3 FLOAT,
    altman_x4 FLOAT,
    altman_x5 FLOAT,
    altman_z_score FLOAT,
    equity_vol FLOAT,
    merton_dd FLOAT,
    merton_pd FLOAT,
    macro_debt_exposure FLOAT,
    liquidity_stress_exposure FLOAT,
    springate_s_score FLOAT,
    springate_distressed INTEGER,
    zmijewski_x_score FLOAT,
    zmijewski_distressed INTEGER,
    distress_probability FLOAT,
    is_distressed INTEGER,
    distress_label INTEGER,
    distress_label_next_year INTEGER,
    systemic_contagion_prob FLOAT,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT distress_ticker_year_uc UNIQUE (ticker, year)
);

CREATE INDEX ix_company_distress_analysis_ticker ON company_distress_analysis(ticker);
CREATE INDEX ix_company_distress_analysis_year ON company_distress_analysis(year);

-- Company financials
CREATE TABLE company_financials (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR NOT NULL,
    year INTEGER NOT NULL,
    total_assets FLOAT,
    current_assets FLOAT,
    total_liabilities FLOAT,
    current_liabilities FLOAT,
    total_equity FLOAT,
    retained_earnings FLOAT,
    net_revenue FLOAT,
    profit_after_tax FLOAT,
    ebit FLOAT,
    interest_expense FLOAT,
    operating_cash_flow FLOAT,
    market_cap FLOAT,
    CONSTRAINT ticker_year_uc UNIQUE (ticker, year)
);

CREATE INDEX ix_company_financials_ticker ON company_financials(ticker);
CREATE INDEX ix_company_financials_year ON company_financials(year);

-- Corporate Merton credit
CREATE TABLE corporate_merton_credit (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR NOT NULL,
    date VARCHAR NOT NULL,
    asset_value FLOAT,
    asset_volatility FLOAT,
    distance_to_default FLOAT,
    default_probability FLOAT,
    total_liabilities FLOAT,
    outstanding_shares FLOAT,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT ticker_date_merton_uc UNIQUE (ticker, date)
);

CREATE INDEX ix_corporate_merton_credit_ticker ON corporate_merton_credit(ticker);
CREATE INDEX ix_corporate_merton_credit_date ON corporate_merton_credit(date);

-- CW info
CREATE TABLE cw_info (
    symbol TEXT PRIMARY KEY,
    underlying TEXT,
    issuer TEXT,
    cw_type TEXT,
    exercise_style TEXT,
    duration TEXT,
    issue_date TEXT,
    listing_date TEXT,
    first_trade_date TEXT,
    last_trade_date TEXT,
    maturity_date TEXT,
    conversion_ratio REAL,
    issue_price REAL,
    strike_price REAL,
    listed_volume REAL,
    crawled_at TEXT
);

-- Macro history
CREATE TABLE macro_history (
    date TEXT,
    symbol TEXT,
    close REAL,
    PRIMARY KEY (date, symbol)
);

-- VN30 gamma exposure
CREATE TABLE vn30_gamma_exposure (
    id SERIAL PRIMARY KEY,
    underlying_symbol VARCHAR NOT NULL,
    date VARCHAR NOT NULL,
    total_gamma_exposure FLOAT,
    net_delta_exposure FLOAT,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT underlying_date_gex_uc UNIQUE (underlying_symbol, date)
);

CREATE INDEX ix_vn30_gamma_exposure_underlying_symbol ON vn30_gamma_exposure(underlying_symbol);
CREATE INDEX ix_vn30_gamma_exposure_date ON vn30_gamma_exposure(date);

-- GARCH vol report
CREATE TABLE garch_vol_report (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR NOT NULL UNIQUE,
    omega FLOAT,
    alpha FLOAT,
    beta FLOAT,
    persistence FLOAT,
    degrees_of_freedom_nu FLOAT,
    is_stable INTEGER,
    garch_forecast_vol_pct FLOAT,
    hist_30d_vol_pct FLOAT,
    deviation_pct FLOAT,
    latest_return_pct FLOAT,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### 1.4 Migrate Data từ SQLite
```bash
# Sau khi setup Supabase và có DATABASE_URL
python scripts/migrate_to_supabase.py
```

---

## Phase 2: Backend Deploy (Render/Railway)

### 2.1 Chuẩn bị Repository
```bash
# Push code lên GitHub
git add .
git commit -m "Prepare for production deployment"
git push origin main
```

### 2.2 Deploy lên Render.com
1. Truy cập https://render.com
2. Sign up/Login với GitHub
3. Click "New +" → "Web Service"
4. Connect GitHub repository `Nahtuna/Finvista`
5. Configure:
   - **Name**: `finvista-backend`
   - **Region**: Singapore
   - **Branch**: `main`
   - **Runtime**: Python 3
   - **Build Command**: `pip install -e .`
   - **Start Command**: `uvicorn src.api.main:app --host 0.0.0.0 --port $PORT`

### 2.3 Environment Variables (Render)
Add these environment variables:
```bash
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.[REF].supabase.co:5432/postgres
JWT_SECRET_KEY=[generate-random-secret-key]
TELEGRAM_BOT_TOKEN=[your-telegram-token]
TELEGRAM_CHAT_ID=[your-chat-id]
GEMINI_API_KEY=[your-gemini-api-key]
```

### 2.4 Upload ML Models
**Option 1**: Include in repository (recommended for small models)
```bash
# Models đã có trong artifacts/ folder
# Render sẽ tự động deploy cùng code
```

**Option 2**: Upload đến cloud storage (cho models lớn)
```bash
# Upload artifacts/ folder lên S3/Google Cloud Storage
# Update code để download models khi start
```

---

## Phase 3: Frontend Deploy (Vercel)

### 3.1 Update Frontend Config
Update `frontend/.env`:
```bash
VITE_API_BASE_URL=https://finvista-backend.onrender.com
```

### 3.2 Deploy lên Vercel
1. Truy cập https://vercel.com
2. Sign up/Login với GitHub
3. "Add New Project" → Import `Nahtuna/Finvista`
4. Configure:
   - **Framework Preset**: Vite
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`

### 3.3 Environment Variables (Vercel)
```bash
VITE_API_BASE_URL=https://finvista-backend.onrender.com
```

---

## Phase 4: Testing & Verification

### 4.1 Test Backend
```bash
# Test API health
curl https://finvista-backend.onrender.com/health

# Test Swagger docs
# Open: https://finvista-backend.onrender.com/docs
```

### 4.2 Test Frontend
```bash
# Open deployed frontend
# https://finvista-frontend.vercel.app
```

### 4.3 Test Database Connection
```bash
# Kiểm tra data đã migrate
# Vào Supabase Dashboard → Table Editor
```

---

## Troubleshooting

### Database Connection Issues
- Check Supabase project status
- Verify DATABASE_URL format
- Ensure Supabase allows connections from Render IP

### ML Models Not Found
- Verify artifacts/ folder included in deployment
- Check file paths in code (use absolute paths)

### CORS Issues
- Add frontend domain to CORS whitelist in FastAPI
- Update `src/api/main.py` CORS settings

### Environment Variables
- Double-check all env vars set correctly
- Regenerate secrets if needed

---

## Cost Estimates

### Supabase (Free Tier)
- 500MB database storage
- 1GB bandwidth/month
- 2 concurrent connections
- **Cost**: $0/month

### Render (Free Tier)
- 512MB RAM
- 0.1 CPU
- Sleeps after 15min inactivity
- **Cost**: $0/month

### Vercel (Hobby Tier)
- 100GB bandwidth
- Unlimited deployments
- **Cost**: $0/month

**Total Monthly Cost**: $0 (Free tiers sufficient for MVP)

---

## Next Steps After Deployment

1. **Monitor performance** với Render Dashboard & Supabase Logs
2. **Setup error tracking** (Sentry)
3. **Configure custom domain** (optional)
4. **Setup automated backups** (Supabase auto-backups)
5. **Scale up** khi cần (Render paid tiers, Supabase Pro)
