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
from datetime import datetime
from typing import List, Optional
from sqlalchemy import (
    create_engine, Column, Integer, String, Float, DateTime, ForeignKey, 
    Boolean, and_, desc
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

# Database Location
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DB_DIR, exist_ok=True)
DATABASE_URL = f"sqlite:///{os.path.join(DB_DIR, 'finvista.db')}"

# Setup Engine and Session
engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False}  # Safe for multi-threaded FastAPI
)
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
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    portfolio = relationship("Portfolio", back_populates="user", uselist=False, cascade="all, delete-orphan")
    positions = relationship("Position", back_populates="user", cascade="all, delete-orphan")
    transactions = relationship("TransactionHistory", back_populates="user", cascade="all, delete-orphan")

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
    proj_3d_flat_pct = Column(Float)
    proj_3d_up_pct = Column(Float)
    proj_3d_down_pct = Column(Float)
    moneyness_category = Column(String)
    
    underlying_distress_prob = Column(Float)
    underlying_is_distressed = Column(Integer)
    underlying_altman_z = Column(Float)
    
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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
