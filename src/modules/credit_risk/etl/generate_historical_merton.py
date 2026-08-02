# -*- coding: utf-8 -*-
"""
🏆 FINVISTA: HISTORICAL DAILY MERTON CREDIT RISK GENERATOR
=========================================================
Calculates daily Merton credit risk parameters (Distance to Default & Default Probability)
for all underlying stocks over the 5-year historical backtest period (2021-2026).
Ensures realistic credit risk hard-gates are applied during walk-forward validation.

Author: samvo
"""

import os
import sys
import pandas as pd
import numpy as np
import warnings
from datetime import datetime
from sqlalchemy import text

warnings.filterwarnings('ignore')

# Force terminal UTF-8 encoding on Windows to avoid print crashes
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Ensure project root is on PYTHONPATH
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.core.database import engine
from src.modules.credit_risk.models.merton_structural_model import solve_merton_model
from src.modules.cw_pricing.models.pricing_core import RISK_FREE_RATE

# VN30 Default Parameters
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
    'VRE': {'shares': 2272000000, 'debt': 10000000000.0, 'equity_vol': 0.312},
    'SSI': {'shares': 1511000000, 'debt': 25000000000000.0, 'equity_vol': 0.295},
    'HDB': {'shares': 2900000000, 'debt': 400000000000000.0, 'equity_vol': 0.210},
    'CTG': {'shares': 4800000000, 'debt': 1800000000000000.0, 'equity_vol': 0.220},
    'TPB': {'shares': 2200000000, 'debt': 300000000000000.0, 'equity_vol': 0.199},
    'VIB': {'shares': 2536840000, 'debt': 350000000000000.0, 'equity_vol': 0.199},
}

def get_outstanding_shares(ticker, conn):
    """Estimate outstanding shares for a stock."""
    if ticker in DEFAULTS_VN30:
        return DEFAULTS_VN30[ticker]['shares']
        
    # Check if there is a record in corporate_merton_credit
    cursor = conn.cursor()
    cursor.execute("SELECT outstanding_shares FROM corporate_merton_credit WHERE ticker = ? ORDER BY date DESC LIMIT 1", (ticker,))
    row = cursor.fetchone()
    if row and row[0]:
        return row[0]
        
    # Estimate from company_financials (market_cap / close price)
    try:
        df_f = pd.read_sql(f"SELECT year, market_cap FROM company_financials WHERE ticker = '{ticker}' AND market_cap > 0 ORDER BY year DESC", conn)
        if not df_f.empty:
            latest_cap = df_f['market_cap'].iloc[0]
            latest_year = df_f['year'].iloc[0]
            df_p = pd.read_sql(f"SELECT close FROM stock_history WHERE symbol = '{ticker}' AND date LIKE '{latest_year}%' LIMIT 1", conn)
            if not df_p.empty:
                price = df_p['close'].iloc[0]
                if price > 0:
                    return latest_cap / price
    except Exception:
        pass
        
    return 200000000.0 # general fallback (200M shares)

def main():
    print("=" * 80)
    print(" [MERTON] GENERATING HISTORICAL DAILY MERTON CREDIT PARAMETERS")
    print("=" * 80)
    
    # 1. Fetch distinct stock tickers
    import sqlite3
    db_path = os.path.join(PROJECT_ROOT, "data", "finvista.db")
    conn = sqlite3.connect(db_path)
    
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT symbol FROM stock_history")
    tickers = [r[0] for r in cursor.fetchall()]
    print(f"[INFO] Found {len(tickers)} stock symbols in database.")
    
    # 2. Load all financial statements for liabilities lookup
    df_fin = pd.read_sql("SELECT ticker, year, total_liabilities FROM company_financials", conn)
    # Pivot to dict for fast O(1) lookup: {ticker: {year: liabilities}}
    fin_map = {}
    for _, row in df_fin.iterrows():
        t = row['ticker']
        y = int(row['year'])
        d = float(row['total_liabilities'] or 0.0)
        if t not in fin_map:
            fin_map[t] = {}
        fin_map[t][y] = d
        
    # Clear existing historical records to avoid duplicates
    print("[INFO] Clearing existing corporate_merton_credit records...")
    cursor.execute("DELETE FROM corporate_merton_credit")
    conn.commit()
    
    merton_records = []
    
    for idx, ticker in enumerate(tickers, 1):
        print(f"[{idx}/{len(tickers)}] Processing {ticker}...", end="", flush=True)
        
        # Fetch price history
        df_price = pd.read_sql(f"SELECT date, close FROM stock_history WHERE symbol = '{ticker}' ORDER BY date ASC", conn)
        if df_price.empty:
            print(" skipped (no price data).")
            continue
            
        # Deduplicate dates to prevent UNIQUE constraint failures
        df_price = df_price.drop_duplicates(subset=['date']).reset_index(drop=True)
            
        # Pre-calculate rolling 60-day volatility
        df_price['log_ret'] = np.log(df_price['close'] / df_price['close'].shift(1))
        df_price['rolling_vol'] = df_price['log_ret'].rolling(60).std() * np.sqrt(252)
        default_vol = DEFAULTS_VN30.get(ticker, {}).get('equity_vol', 0.35)
        df_price['rolling_vol'] = df_price['rolling_vol'].fillna(default_vol)
        
        # Outstanding shares (stable over time for credit proxy)
        shares = get_outstanding_shares(ticker, conn)
        
        ticker_records = []
        for _, row in df_price.iterrows():
            date_str = row['date']
            close_price = row['close']
            equity_vol = row['rolling_vol']
            
            # Map date to year (lagged by 1 year to avoid look-ahead bias)
            date_yr = pd.to_datetime(date_str).year
            liab_year = date_yr - 1
            
            # Fetch liabilities
            liabilities = 0.0
            if ticker in fin_map:
                liabilities = fin_map[ticker].get(liab_year, 0.0)
                if liabilities <= 0.0:
                    # try current year
                    liabilities = fin_map[ticker].get(date_yr, 0.0)
                    if liabilities <= 0.0:
                        # try any available year
                        available_yrs = sorted(fin_map[ticker].keys())
                        if available_yrs:
                            liabilities = fin_map[ticker][available_yrs[-1]]
                            
            if liabilities <= 0.0:
                # Fallback to defaults or a proxy (e.g. 50% of asset estimate)
                liabilities = DEFAULTS_VN30.get(ticker, {}).get('debt', 10000000000.0)
                
            equity_val = close_price * shares
            
            # Solve Merton KMV Model
            res = solve_merton_model(
                equity_val=equity_val,
                equity_vol=equity_vol,
                total_debt=liabilities,
                T=1.0,
                risk_free_rate=RISK_FREE_RATE,
                dividend_yield=0.0
            )
            
            ticker_records.append((
                ticker,
                date_str,
                float(res['asset_value']),
                float(res['asset_volatility']),
                float(res['distance_to_default']),
                float(res['default_probability']),
                float(liabilities),
                float(shares),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))
            
        merton_records.extend(ticker_records)
        print(f" OK ({len(ticker_records)} days generated).")
        
    # 3. Batch insert using sqlite3 executemany (ultra-fast)
    print(f"\n[INFO] Saving {len(merton_records):,} records to corporate_merton_credit table...")
    insert_query = """
        INSERT INTO corporate_merton_credit 
        (ticker, date, asset_value, asset_volatility, distance_to_default, default_probability, total_liabilities, outstanding_shares, last_updated)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    cursor.executemany(insert_query, merton_records)
    conn.commit()
    
    # 4. Sync latest values back to CompanyDistressAnalysis for integration check
    print("[INFO] Synchronizing latest Merton PD back to CompanyDistressAnalysis...")
    try:
        # Find latest merton record per ticker
        latest_merton_df = pd.read_sql("""
            SELECT ticker, distance_to_default, default_probability 
            FROM corporate_merton_credit 
            WHERE id IN (SELECT MAX(id) FROM corporate_merton_credit GROUP BY ticker)
        """, conn)
        
        for _, row in latest_merton_df.iterrows():
            ticker = row['ticker']
            dd = row['distance_to_default']
            pd_val = row['default_probability']
            
            # Update company_distress_analysis for the latest year (2025)
            cursor.execute("""
                UPDATE company_distress_analysis 
                SET merton_dd = ?, merton_pd = ?, distress_probability = MAX(IFNULL(distress_probability, 0.0), ?),
                    is_distressed = CASE WHEN MAX(IFNULL(distress_probability, 0.0), ?) >= 0.50 THEN 1 ELSE is_distressed END
                WHERE ticker = ? AND year = 2025
            """, (dd, pd_val, pd_val, pd_val, ticker))
        conn.commit()
        print("   Synchronized successfully!")
    except Exception as sync_err:
        print(f"   Warning: Could not sync latest Merton to CompanyDistressAnalysis: {sync_err}")
        
    conn.close()
    print("=" * 80)
    print("[SUCCESS] Historical daily Merton credit risk parameters successfully populated!")
    print("=" * 80)

if __name__ == "__main__":
    main()
