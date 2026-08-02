# -*- coding: utf-8 -*-
"""
🏆 FINVISTA: SQL persISTENCE LAYER (SQLAlchemy SQLite Database)
============================================================
Establishes a robust, production-ready relation database schema.
Transitions storage from static CSV/JSON files to a transactional SQLite DB.
Provides schemas for Users, Portfolios, Positions, History, and Market Opportunities.

Author: samvo
"""

import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from sqlalchemy import (
    create_engine, Column, Integer, String, Float, DateTime, ForeignKey, 
    Boolean, and_, desc
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

# Load environment variables
load_dotenv()

# Database Location
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DB_DIR, exist_ok=True)

# Fetch from env with safe fallback
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    DATABASE_URL = f"sqlite:///{os.path.join(DB_DIR, 'finvista.db')}"
else:
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Setup Engine and Session
if "sqlite" in DATABASE_URL:
    engine = create_engine(
        DATABASE_URL, 
        connect_args={"check_same_thread": False}  # Safe for multi-threaded FastAPI
    )
else:
    engine = create_engine(DATABASE_URL)

# Enable SQLite WAL (Write-Ahead Logging) mode and high-performance local tuning
from sqlalchemy import event
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if DATABASE_URL and "sqlite" in DATABASE_URL:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.execute("PRAGMA cache_size=-64000;")       # Use 64MB cache instead of default 2MB
        cursor.execute("PRAGMA temp_store=MEMORY;")       # Keep temporary tables and indexes in RAM
        cursor.execute("PRAGMA mmap_size=268435456;")     # Enable memory-mapped I/O up to 256MB for ultra-fast reads
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ==========================================
# 1. DATABASE MODELS
# ==========================================

class User(Base):
    """SaaS User Accounts for authentication & account isolation."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    portfolio = relationship("Portfolio", back_populates="user", uselist=False, cascade="all, delete-orphan")
    positions = relationship("Position", back_populates="user", cascade="all, delete-orphan")
    transactions = relationship("TransactionHistory", back_populates="user", cascade="all, delete-orphan")
    nav_history = relationship("PortfolioNavHistory", back_populates="user", cascade="all, delete-orphan")

class Portfolio(Base):
    """User balance, tracks cash and initial capital."""
    __tablename__ = "portfolios"
    
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    cash = Column(Float, default=100000000.0)
    initial_cash = Column(Float, default=100000000.0)
    
    # Relationships
    user = relationship("User", back_populates="portfolio")

class Position(Base):
    """User active paper trading open positions."""
    __tablename__ = "positions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    symbol = Column(String, nullable=False, index=True)
    underlying = Column(String, nullable=True)
    qty = Column(Integer, nullable=False)
    buy_price = Column(Float, nullable=False)
    buy_date = Column(String, nullable=False)  # ISO Timestamp string
    settlement_date = Column(String, nullable=False)  # ISO Timestamp string
    total_cost = Column(Float, nullable=False)
    score_at_buy = Column(Float, nullable=True)
    days_at_buy = Column(Integer, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="positions")

class TransactionHistory(Base):
    """User completed paper trading historical logs."""
    __tablename__ = "transaction_history"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    symbol = Column(String, nullable=False, index=True)
    underlying = Column(String, nullable=True)
    type = Column(String, nullable=False)  # BUY or SELL
    qty = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    value = Column(Float, nullable=False)
    fee = Column(Float, nullable=False)
    date = Column(String, nullable=False)  # ISO Timestamp string
    reason = Column(String, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="transactions")

class PortfolioNavHistory(Base):
    """Time-series checkpoints of User Portfolio NAV for charting."""
    __tablename__ = "portfolio_nav_history"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    total_nav = Column(Float, nullable=False)
    cash = Column(Float, nullable=False)
    positions_value = Column(Float, nullable=False)
    date = Column(String, nullable=False)  # ISO Timestamp string (e.g. YYYY-MM-DD HH:MM:SS)
    
    # Relationships
    user = relationship("User", back_populates="nav_history")

class MarketOpportunity(Base):
    """
    Quantitative analysis results for all active Covered Warrants in live market.
    Serves as persistent cache. Endpoints read instantly from here.
    """
    __tablename__ = "market_opportunities"
    
    symbol = Column(String, primary_key=True, index=True)
    underlying = Column(String, index=True)
    issuer = Column(String, index=True)
    price = Column(Float)
    price_change_pct = Column(Float)
    intrinsic_value = Column(Float)
    break_even_price = Column(Float)
    premium_pct = Column(Float)
    risk_monthly_pct = Column(Float)
    gearing = Column(Float)
    days_to_maturity = Column(Integer, index=True)
    score = Column(Float, index=True)
    decision_signal = Column(String)
    
    underlying_price = Column(Float)
    ratio = Column(String)
    strike_price = Column(Float)
    volume = Column(Float)
    turnover = Column(Float)
    implied_volatility_pct = Column(Float)
    historical_volatility_pct = Column(Float)
    delta = Column(Float)
    gamma = Column(Float)
    theta_burn_day = Column(Float)
    vega = Column(Float)
    prob_itm = Column(Float)
    theoretical_price = Column(Float)
    upside_pct = Column(Float)
    garch_theoretical_price = Column(Float)
    garch_upside_pct = Column(Float)
    merton_theoretical_price = Column(Float)
    merton_upside_pct = Column(Float)
    proj_3d_flat_pct = Column(Float)
    proj_3d_up_pct = Column(Float)
    proj_3d_down_pct = Column(Float)
    moneyness_category = Column(String)
    
    underlying_distress_prob = Column(Float)
    underlying_is_distressed = Column(Integer)
    underlying_altman_z = Column(Float)
    
    # DebtRank Network Contagion Risk
    underlying_systemic_prob = Column(Float)
    underlying_systemic_delta = Column(Float)
    underlying_systemic_is_distressed = Column(Integer)
    
    # Banking specific health metrics (CAMELS-lite)
    underlying_nim = Column(Float)
    underlying_npl = Column(Float)
    underlying_casa = Column(Float)
    underlying_car = Column(Float)
    
    last_updated = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class CWHistoricalPrice(Base):
    """Time-series historical price data for Covered Warrants."""
    __tablename__ = "cw_history"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True, nullable=False)
    date = Column(String, index=True, nullable=False)  # YYYY-MM-DD
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Float)
    ref_price = Column(Float)

class StockHistoricalPrice(Base):
    """Time-series historical price data for Underlying Stocks."""
    __tablename__ = "stock_history"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True, nullable=False)
    date = Column(String, index=True, nullable=False)  # YYYY-MM-DD
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Float)
    ref_price = Column(Float)

class AIAnalysisMemory(Base):
    """Long-term experience memory for AI Committee decisions."""
    __tablename__ = "ai_analysis_memory"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True, nullable=False)
    underlying = Column(String, index=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    decision = Column(String)  # STRONG BUY, BUY, SKIP, etc.
    consensus_score = Column(Float)
    rationale_summary = Column(String)
    
    # Quantitative context at time of analysis
    price_at_analysis = Column(Float)
    underlying_price_at_analysis = Column(Float)
    iv_at_analysis = Column(Float)
    delta_at_analysis = Column(Float)
    days_to_maturity = Column(Integer)
    
    # Outcome tracking (Updated by backtest utility)
    is_correct = Column(Boolean, nullable=True)
    max_upside_pct = Column(Float, nullable=True)
    result_commentary = Column(String, nullable=True)

class CorporateNews(Base):
    """Financial news related to warrants, underlying stocks, or issuers."""
    __tablename__ = "corporate_news"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True, nullable=False) # Can be CW code or Stock ticker
    title = Column(String, nullable=False)
    link = Column(String, unique=True, nullable=False)
    date = Column(String)  # YYYY-MM-DD HH:MM
    source = Column(String, default="Vietstock")
    summary = Column(String)
    category = Column(String) # e.g. "Chứng quyền", "Cổ phiếu cơ sở", "Tổ chức phát hành"
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class CorporateEvent(Base):
    """Corporate events like dividends, meetings, or issuance for underlying stocks."""
    __tablename__ = "corporate_events"
    
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, index=True, nullable=False) # Usually Stock ticker
    event_date = Column(String, index=True) # YYYY-MM-DD
    event_type = Column(String) # e.g. "Cổ tức tiền mặt", "Thưởng cổ phiếu"
    description = Column(String)
    last_updated = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class CompanyDistressAnalysis(Base):
    """Derived credit analysis metrics including Altman Z, Springate, Zmijewski, and distress probabilities."""
    __tablename__ = "company_distress_analysis"
    
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, index=True, nullable=False)
    year = Column(Integer, nullable=False)
    industry = Column(String)
    roaa = Column(Float)
    roae = Column(Float)
    industry_adjusted_roaa = Column(Float)
    industry_roaa_percentile = Column(Float)
    industry_adjusted_roae = Column(Float)
    industry_roae_percentile = Column(Float)
    industry_adjusted_debt_ratio = Column(Float)
    industry_debt_ratio_percentile = Column(Float)
    current_ratio = Column(Float)
    working_capital = Column(Float)
    working_capital_to_assets = Column(Float)
    ocf_to_current_liabilities = Column(Float)
    cash_ratio = Column(Float)
    ocf_to_total_debt = Column(Float)
    cfo_interest_coverage = Column(Float)
    roa = Column(Float)
    roe = Column(Float)
    operating_margin = Column(Float)
    ebit_to_assets = Column(Float)
    ocf_to_pat = Column(Float)
    equity_multiplier = Column(Float)
    ebit_to_interest = Column(Float)
    icr = Column(Float)
    debt_to_equity = Column(Float)
    debt_ratio = Column(Float)
    company_size = Column(Float)
    revenue_growth = Column(Float)
    assets_growth = Column(Float)
    altman_x1 = Column(Float)
    altman_x2 = Column(Float)
    altman_x3 = Column(Float)
    altman_x4 = Column(Float)
    altman_x5 = Column(Float)
    altman_z_score = Column(Float)
    equity_vol = Column(Float)
    merton_dd = Column(Float)
    merton_pd = Column(Float)
    macro_debt_exposure = Column(Float)
    liquidity_stress_exposure = Column(Float)
    springate_s_score = Column(Float)
    springate_distressed = Column(Integer)
    zmijewski_x_score = Column(Float)
    zmijewski_distressed = Column(Integer)
    distress_probability = Column(Float)
    is_distressed = Column(Integer)
    distress_label = Column(Integer)
    distress_label_next_year = Column(Integer)
    systemic_contagion_prob = Column(Float)
    last_updated = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class CompanyFinancial(Base):
    """Annual financial statement variables for corporate analysis."""
    __tablename__ = "company_financials"
    
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, index=True, nullable=False)
    year = Column(Integer, nullable=False)
    total_assets = Column(Float)
    current_assets = Column(Float)
    total_liabilities = Column(Float)
    current_liabilities = Column(Float)
    total_equity = Column(Float)
    retained_earnings = Column(Float)
    net_revenue = Column(Float)
    profit_after_tax = Column(Float)
    ebit = Column(Float)
    interest_expense = Column(Float)
    operating_cash_flow = Column(Float)
    market_cap = Column(Float)

class CorporateMertonCredit(Base):
    """Daily Merton distance-to-default and default probabilities for corporations."""
    __tablename__ = "corporate_merton_credit"
    
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, index=True, nullable=False)
    date = Column(String, index=True, nullable=False)  # YYYY-MM-DD
    asset_value = Column(Float)
    asset_volatility = Column(Float)
    distance_to_default = Column(Float)
    default_probability = Column(Float)
    total_liabilities = Column(Float)
    outstanding_shares = Column(Float)
    last_updated = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


# ==========================================
# 2. HELPER INITIALIZER
# ==========================================

def init_db():
    """Create schemas and pre-populate with default DEMO user accounts."""
    Base.metadata.create_all(bind=engine)
    
    # Initialize a default demo user if not already present
    db = SessionLocal()
    try:
        demo_user = db.query(User).filter(User.username == "demo").first()
        if not demo_user:
            # Simple demo account (hashed password is 'finvista123' for demonstration)
            demo_user = User(
                username="demo",
                hashed_password="$pbkdf2-sha256$29000$h6UqC5q9G6S1.$D9y1Kz77tFpT5q0x4Z0u1u" 
            )
            db.add(demo_user)
            db.commit()
            db.refresh(demo_user)
            
            # Associate empty Portfolio
            demo_portfolio = Portfolio(
                user_id=demo_user.id,
                cash=100000000.0,
                initial_cash=100000000.0
            )
            db.add(demo_portfolio)
            db.commit()
            print("🚀 Successfully initialized Finvista database schemas and default demo user!")
    except Exception as e:
        print(f"⚠️ Error initializing database: {e}")
        db.rollback()
    finally:
        db.close()

# Initialize on import
init_db()
