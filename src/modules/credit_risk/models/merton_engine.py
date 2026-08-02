# -*- coding: utf-8 -*-
"""
🏗️ FINVISTA: MERTON STRUCTURAL RISK ENGINE (REAL-TIME)
======================================================
Calculates Distance to Default (DD) and Probability of Default (PD)
using the Merton Model framework adjusted for daily price volatility.

Formula:
  DD = [ln(V/D) + (r - 0.5*sigma_V^2)*T] / (sigma_V * sqrt(T))
  V: Market Value of Assets (approx Market Cap + Total Debt)
  D: Total Debt (Face value)
  sigma_V: Asset Volatility (approx (E/V) * Equity_Vol)
"""

import numpy as np
import pandas as pd
from scipy.stats import norm
from src.core.database import engine
from src.core.utils import logger

def calculate_merton_dd_realtime(ticker: str, current_price: float, risk_free_rate: float = 0.04) -> dict:
    """
    Calculates the Merton Distance to Default for a single ticker using 
    daily price action and latest balance sheet data.
    """
    try:
        # 1. Fetch latest debt from DB
        query = f"""
            SELECT total_liabilities, total_assets 
            FROM company_financials 
            WHERE ticker = '{ticker}' 
            ORDER BY year DESC LIMIT 1
        """
        financials = pd.read_sql(query, engine)
        
        # 2. Fetch shares outstanding from Merton Credit table or fallback
        query_shares = f"SELECT outstanding_shares FROM corporate_merton_credit WHERE ticker = '{ticker}' ORDER BY date DESC LIMIT 1"
        shares_info = pd.read_sql(query_shares, engine)
        
        if financials.empty:
            return {'ticker': ticker, 'status': 'insufficient_data'}

        total_debt = float(financials['total_liabilities'].iloc[0])
        
        if not shares_info.empty and shares_info['outstanding_shares'].iloc[0] > 0:
            shares = float(shares_info['outstanding_shares'].iloc[0])
        else:
            # Fallback: Try to estimate shares from Market Cap in financials if available
            mcap_fin = float(financials.get('market_cap', [0]).iloc[0] or 0)
            if mcap_fin > 0:
                # This is a very rough proxy if we don't have shares
                shares = mcap_fin / current_price 
            else:
                return {'ticker': ticker, 'status': 'insufficient_data (shares)'}
        
        market_cap = current_price * shares
        
        # 2. Fetch 60-day historical volatility (Equity Vol)
        # We proxy this from stock_history
        query_hist = f"""
            SELECT close FROM stock_history 
            WHERE symbol = '{ticker}' 
            ORDER BY date DESC LIMIT 60
        """
        prices_df = pd.read_sql(query_hist, engine)
        if len(prices_df) < 20:
            equity_vol = 0.35 # Default high vol for safety
        else:
            returns = np.log(prices_df['close'] / prices_df['close'].shift(-1)).dropna()
            equity_vol = returns.std() * np.sqrt(252)

        # 3. Merton Structural Calculations
        T = 1.0 # 1-year horizon
        r = risk_free_rate
        
        # Asset Value (V) approx Market Cap + Debt
        V = market_cap + total_debt
        # Asset Volatility (sigma_V) approx (E/V) * sigma_E
        sigma_v = (market_cap / V) * equity_vol
        sigma_v = max(0.01, sigma_v) # Floor vol

        # Distance to Default (DD)
        # DD = [ln(V/D) + (r - 0.5 * sigma_v^2) * T] / (sigma_v * sqrt(T))
        d_val = total_debt if total_debt > 0 else 1.0
        dd = (np.log(V / d_val) + (r + 0.5 * sigma_v**2) * T) / (sigma_v * np.sqrt(T))
        
        # Probability of Default (PD)
        pd_val = norm.cdf(-dd)

        # 4. Assessment
        status = 'HEALTHY'
        if dd < 1.5 or pd_val > 0.05:
            status = 'DISTRESSED'
        elif dd < 2.5:
            status = 'WATCH'

        return {
            'ticker': ticker,
            'market_cap_bn': market_cap / 1e9,
            'debt_bn': total_debt / 1e9,
            'equity_vol': equity_vol,
            'asset_vol': sigma_v,
            'merton_dd': dd,
            'merton_pd': pd_val,
            'status': status
        }
    except Exception as e:
        logger.error(f"❌ Merton calculation error for {ticker}: {e}")
        return {'ticker': ticker, 'status': 'error'}

def batch_update_merton_scores(tickers_prices: list):
    """
    Updates the Merton scores for a list of (ticker, price) tuples.
    Useful for scanning the entire market.
    """
    results = []
    for ticker, price in tickers_prices:
        score = calculate_merton_dd_realtime(ticker, price)
        results.append(score)
    return pd.DataFrame(results)
