# -*- coding: utf-8 -*-
"""
🏆 FINVISTA: DAILY MERTON STRUCTURAL CREDIT RISK INGESTOR
=========================================================
Queries underlying stock tickers, gets latest liabilities, fetches outstanding shares,
extracts spot prices, solves Merton Model, and caches output to SQLite.

Author: samvo
"""

import os
import sys
import requests
import json
import pandas as pd
import numpy as np
from datetime import datetime, timezone
import contextlib

# Ensure project root is on PYTHONPATH
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.core.database import (
    SessionLocal, CorporateMertonCredit, CompanyFinancial, 
    MarketOpportunity, CompanyDistressAnalysis
)
from src.modules.credit_risk.models.merton_structural_model import solve_merton_model
from src.modules.cw_pricing.models.pricing_core import RISK_FREE_RATE
from src.core.utils import logger, random_sleep

# Default shares and debt for VN30 stocks to ensure robust fallback offline
DEFAULTS_VN30 = {
    'HPG': {'shares': 5814861120, 'debt': 100000000000000.0, 'equity_vol': 0.208},
    'FPT': {'shares': 1270000000, 'debt': 30000000000000.0, 'equity_vol': 0.331},
    'ACB': {'shares': 3880000000, 'debt': 600000000000000.0, 'equity_vol': 0.185},
    'TCB': {'shares': 3518000000, 'debt': 700000000000000.0, 'equity_vol': 0.270},
    'MBB': {'shares': 5214000000, 'debt': 850000000000000.0, 'equity_vol': 0.187},
    'STB': {'shares': 1885000000, 'debt': 550000000000000.0, 'equity_vol': 0.406},
    'VPB': {'shares': 7933000000, 'debt': 700000000000000.0, 'equity_vol': 0.281},
    'VNM': {'shares': 2090000000, 'debt': 15000000000000.0, 'equity_vol': 0.153},
    'MWG': {'shares': 1460000000, 'debt': 25000000000000.0, 'equity_vol': 0.326},
    'VIC': {'shares': 3823000000, 'debt': 290000000000000.0, 'equity_vol': 0.484},
    'VHM': {'shares': 4354000000, 'debt': 200000000000000.0, 'equity_vol': 0.587},
    'MSN': {'shares': 1430000000, 'debt': 110000000000000.0, 'equity_vol': 0.224},
    'VRE': {'shares': 2272000000, 'debt': 10000000000000.0, 'equity_vol': 0.312},
    'SSI': {'shares': 1511000000, 'debt': 25000000000000.0, 'equity_vol': 0.295},
    'HDB': {'shares': 2900000000, 'debt': 400000000000000.0, 'equity_vol': 0.210},
    'CTG': {'shares': 4800000000, 'debt': 1800000000000000.0, 'equity_vol': 0.220},
    'TPB': {'shares': 2200000000, 'debt': 300000000000000.0, 'equity_vol': 0.199},
    'VIB': {'shares': 2536840000, 'debt': 350000000000000.0, 'equity_vol': 0.199},
}

def get_latest_spot_prices(tickers: list) -> dict:
    """Fetch latest stock prices in a single batch from Vietcap trading API."""
    url = "https://trading.vietcap.com.vn/api/price/symbols/getList"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Content-Type": "application/json",
        "Referer": "https://trading.vietcap.com.vn/quote"
    }
    try:
        resp = requests.post(url, headers=headers, json={"symbols": tickers}, timeout=10)
        if resp.status_code == 200:
            return {
                item['listingInfo']['symbol']: float(item['matchPrice'].get('matchPrice', 0) or item['matchPrice'].get('referencePrice', 0) or 0)
                for item in resp.json()
            }
    except Exception as e:
        logger.warning(f"⚠️ Failed to batch-fetch spot prices from Vietcap: {e}")
    return {}

def fetch_outstanding_shares_vnstock(ticker: str) -> float:
    """Fetch outstanding shares via vnstock 4.0.4 Company overview."""
    try:
        # Silence vnstock notices/prints
        with contextlib.redirect_stdout(None), contextlib.redirect_stderr(None):
            import vnstock
            c = vnstock.Company(source='VCI', symbol=ticker)
            overview = c.overview()
            if not overview.empty and 'outstandingShares' in overview.columns:
                val = float(overview['outstandingShares'].iloc[0])
                if val > 0:
                    return val
    except BaseException as e:
        logger.warning(f"⚠️ Could not fetch vnstock outstanding shares for {ticker}: {e}")
    
    # Fallback to defaults
    fallback = DEFAULTS_VN30.get(ticker, {}).get('shares', 100000000.0)
    return float(fallback)

def run_merton_ingestion(limit_tickers: list = None):
    """Orchestrates daily Merton credit risk solver and caches results in DB."""
    logger.info("🎬 Starting Merton Structural Credit Risk Daily Ingestion...")
    db = SessionLocal()
    
    try:
        # 1. Retrieve target tickers
        if limit_tickers:
            tickers = limit_tickers
        else:
            # Query active underlying stocks in opportunities or history
            active_underlyings = db.query(MarketOpportunity.underlying).distinct().all()
            tickers = [r[0] for r in active_underlyings if r[0]]
            
            # If empty, fall back to VN30 defaults
            if not tickers:
                tickers = list(DEFAULTS_VN30.keys())
                
        logger.info(f"🎯 Target underlying tickers: {tickers}")
        
        # 2. Get latest spot prices in one request
        spot_prices = get_latest_spot_prices(tickers)
        
        # 3. For each ticker, solve Merton and save
        date_str = datetime.now().strftime('%Y-%m-%d')
        updated_count = 0
        
        for idx, ticker in enumerate(tickers):
            # Resolve Spot Price S (VND)
            # Spot API returns price in thousands or units? Vietcap returns in units (e.g. 28500.0 for HPG)
            price = spot_prices.get(ticker, 0.0)
            if price <= 0:
                # Try fallback from stock_history table
                from sqlalchemy import text
                try:
                    last_price_row = db.execute(
                        text("SELECT close FROM stock_history WHERE symbol = :sym ORDER BY date DESC LIMIT 1"),
                        {"sym": ticker}
                    ).fetchone()
                    if last_price_row:
                        price = float(last_price_row[0])
                except Exception:
                    pass
            
            if price <= 0:
                logger.warning(f"⏩ Ticker {ticker} skipped: price is not available.")
                continue
                
            # Resolve Total Liabilities D
            # Try to get latest from company_financials table
            liabilities = 0.0
            latest_fin = db.query(CompanyFinancial).filter(CompanyFinancial.ticker == ticker).order_by(CompanyFinancial.year.desc()).first()
            if latest_fin:
                liabilities = float(latest_fin.total_liabilities or 0.0)
                
            if liabilities <= 0:
                # Try fallback
                liabilities = DEFAULTS_VN30.get(ticker, {}).get('debt', 10000000000.0)
                
            # Resolve Outstanding Shares N
            shares = 0.0
            try:
                # Try to load from database first to avoid hitting vnstock API rate limits
                last_merton = db.query(CorporateMertonCredit).filter(
                    CorporateMertonCredit.ticker == ticker
                ).order_by(CorporateMertonCredit.date.desc()).first()
                if last_merton and last_merton.outstanding_shares:
                    shares = float(last_merton.outstanding_shares)
            except Exception as db_ex:
                logger.warning(f"⚠️ Could not load outstanding shares from DB for {ticker}: {db_ex}")
                
            if shares <= 0:
                shares = fetch_outstanding_shares_vnstock(ticker)
            
            # Calculate Equity Value E = S * N
            equity_val = price * shares
            
            # Resolve Equity Volatility (use 40-day HV or default)
            equity_vol = DEFAULTS_VN30.get(ticker, {}).get('equity_vol', 0.35)
            # Try to calculate from database if history is available
            try:
                from sqlalchemy import text
                prices_rows = db.execute(
                    text("SELECT close FROM stock_history WHERE symbol = :sym ORDER BY date DESC LIMIT 60"),
                    {"sym": ticker}
                ).fetchall()
                if len(prices_rows) >= 15:
                    p_list = [float(r[0]) for r in prices_rows]
                    p_list.reverse() # chronological
                    log_ret = np.log(np.array(p_list[1:]) / np.array(p_list[:-1]))
                    equity_vol = float(log_ret.std() * np.sqrt(252))
            except Exception:
                pass
                
            # Run Merton Solver
            # T = 1.0 (1 year standard KMV horizon)
            res = solve_merton_model(
                equity_val=equity_val,
                equity_vol=equity_vol,
                total_debt=liabilities,
                T=1.0,
                risk_free_rate=RISK_FREE_RATE,
                dividend_yield=0.0
            )
            
            # 4. Save to corporate_merton_credit table
            # Try to find existing record for today
            existing = db.query(CorporateMertonCredit).filter(
                CorporateMertonCredit.ticker == ticker,
                CorporateMertonCredit.date == date_str
            ).first()
            
            if not existing:
                existing = CorporateMertonCredit(ticker=ticker, date=date_str)
                db.add(existing)
                
            existing.asset_value = res['asset_value']
            existing.asset_volatility = res['asset_volatility']
            existing.distance_to_default = res['distance_to_default']
            existing.default_probability = res['default_probability']
            existing.total_liabilities = liabilities
            existing.outstanding_shares = shares
            
            # 5. Sync to CompanyDistressAnalysis for Credit Pipeline integration
            # We find the latest year analysis for this ticker
            distress_rec = db.query(CompanyDistressAnalysis).filter(
                CompanyDistressAnalysis.ticker == ticker
            ).order_by(CompanyDistressAnalysis.year.desc()).first()
            
            if distress_rec:
                distress_rec.equity_vol = equity_vol
                distress_rec.merton_dd = res['distance_to_default']
                distress_rec.merton_pd = res['default_probability']
                # Sync distress probability if Merton PD represents higher risk
                if res['default_probability'] > 0.0:
                    # Blend or override
                    distress_rec.distress_probability = max(distress_rec.distress_probability or 0.0, res['default_probability'])
                    if distress_rec.distress_probability >= 0.50:
                        distress_rec.is_distressed = 1
            
            # 6. Update MarketOpportunity table to trigger hard gates immediately
            warrants = db.query(MarketOpportunity).filter(MarketOpportunity.underlying == ticker).all()
            for w in warrants:
                w.underlying_distress_prob = max(w.underlying_distress_prob or 0.0, res['default_probability'])
                if w.underlying_distress_prob >= 0.50:
                    w.underlying_is_distressed = 1
                    w.decision_signal = "SKIP (DISTRESSED ASSET)"
                    w.score = 0.0
            
            updated_count += 1
            logger.info(f"   ✅ {ticker:<6} -> Spot: {price:,.0f}đ | DD: {res['distance_to_default']:.3f} | PD: {res['default_probability']:.6%}")
            
            # Short throttle to be nice to vnstock API
            random_sleep(0.5, 1.0)
            
        db.commit()
        logger.info(f"🎉 Successfully completed Merton Credit calculations for {updated_count} underlying symbols!")
        
    except Exception as e:
        logger.error(f"❌ Error during Merton Credit ingestion: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    run_merton_ingestion()
