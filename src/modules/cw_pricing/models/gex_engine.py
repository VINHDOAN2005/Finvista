# -*- coding: utf-8 -*-
"""
🔬 FINVISTA: GAMMA EXPOSURE (GEX) ENGINE
========================================
Calculates the aggregate Gamma Exposure for the Vietnamese Covered Warrants market.
Identifies "Gamma Walls" and "Magnets" created by issuer hedging activities.

Author: samvo
"""

import os
import sys
import requests
import json
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from datetime import datetime

# Ensure project root is on PYTHONPATH
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.core.utils import logger
from src.modules.cw_pricing.models.pricing_core import calculate_gamma, parse_ratio, RISK_FREE_RATE
from src.modules.cw_pricing.backtest.fetcher import fetch_market_cw_data
    
def get_ssi_cw_volume_data(symbol: str) -> Dict[str, Any]:
    """Fetch outstanding quantity and total listed quantity from SSI."""
    url = "https://iboard.ssi.com.vn/gateway/graphql"
    query = """
    query stockDetails($symbol: String) {
      stockDetails(symbol: $symbol) {
        symbol
        totalListedQty
        outstandingQty
      }
    }
    """
    payload = {
        "operationName": "stockDetails",
        "variables": {"symbol": symbol},
        "query": query
    }
    headers = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=5)
        if r.status_code == 200:
            return r.json().get("data", {}).get("stockDetails", {})
    except: pass
    return {}

def calculate_aggregate_gex(underlying_symbol: str, spot_price: Optional[float] = None) -> Dict[str, Any]:
    """
    Calculate the total GEX for an underlying stock based on its active CWs.
    GEX = Gamma * Open Interest (Outstanding Qty) * Underlying Price
    
    In VN market, Retail buys Calls -> Dealer is Short Call (Short Gamma).
    In the rare case of Puts, Retail buys Puts -> Dealer is Short Put (Short Gamma).
    """
    print(f"📊 Calculating GEX for {underlying_symbol}...")
    
    # 1. Fetch all active CWs for this underlying
    cw_df = fetch_market_cw_data()
    if cw_df.empty:
        return {"error": "Failed to fetch market CW data."}
        
    underlying_cws = cw_df[cw_df['B_MaCPCS'] == underlying_symbol].copy()
    if underlying_cws.empty:
        return {"error": f"No active warrants found for {underlying_symbol}."}
        
    s_price = spot_price or underlying_cws['hidden_underlying_price'].iloc[0]
    if not s_price or s_price == 0:
        return {"error": "Underlying price not available."}

    # 2. For each CW, get Greeks and Volume
    gex_data = []
    now = datetime.now()
    
    for _, row in underlying_cws.iterrows():
        symbol = row['A_MaCW']
        strike = row['R_Strike']
        ratio = parse_ratio(row['hidden_ratio'])
        maturity_date = pd.to_datetime(row['Q_DaoHan'])
        days_to_expiry = (maturity_date - now).days
        
        if days_to_expiry <= 0: continue
        
        # Determine Option Type (VN market is 99% Calls, but we prepare for Puts)
        # Usually symbols starting with 'C' are Calls, 'P' are Puts
        option_type = 'call'
        if symbol.startswith('P'): option_type = 'put'
        
        # Use a default IV or calculate if possible
        iv = 0.50 # Benchmark fallback
        
        # Calculate Gamma (per warrant unit, adjusted for ratio)
        gamma = calculate_gamma(s_price, strike, days_to_expiry / 365.0, RISK_FREE_RATE, iv)
        gamma_adj = gamma / ratio
        
        # Dealer position: If retail buys, dealer is SHORT
        # Dealer Gamma = -Gamma (for both calls and puts)
        dealer_gamma = -gamma_adj
        
        # Get Outstanding Volume
        vol_info = get_ssi_cw_volume_data(symbol)
        outstanding = float(vol_info.get("outstandingQty", 0) or row['D_Volume'])
        
        # GEX Calculation (VND per 1% move)
        # GEX = Dealer_Gamma * Outstanding * StockPrice * 0.01
        gex_val = dealer_gamma * outstanding * s_price * 0.01
        
        gex_data.append({
            "symbol": symbol,
            "strike": strike,
            "gamma": dealer_gamma,
            "volume": outstanding,
            "gex": gex_val,
            "type": option_type
        })
        
    if not gex_data:
        return {"error": "No active warrants with valid parameters found."}
        
    gex_df = pd.DataFrame(gex_data)
    total_gex = gex_df['gex'].sum()
    
    # Identify key walls (strikes with highest absolute GEX)
    walls = gex_df.groupby('strike')['gex'].sum().sort_values(ascending=True).head(3)
    
    return {
        "underlying": underlying_symbol,
        "price": s_price,
        "total_gex": total_gex,
        "walls": walls.to_dict(),
        "details": gex_df.to_dict(orient='records')
    }

def calculate_gex_profile(underlying_symbol: str, price_range_pct: float = 0.15) -> Dict[str, Any]:
    """
    Calculates GEX across a range of prices to find the 'Zero Gamma' or 'Gamma Flip' level.
    """
    res = calculate_aggregate_gex(underlying_symbol)
    if "error" in res: return res
    
    base_price = res['price']
    prices = np.linspace(base_price * (1 - price_range_pct), base_price * (1 + price_range_pct), 50)
    
    profile = []
    for p in prices:
        gex_at_p = calculate_aggregate_gex(underlying_symbol, spot_price=p)
        profile.append({
            "price": p,
            "total_gex": gex_at_p['total_gex']
        })
        
    profile_df = pd.DataFrame(profile)
    
    # Find Zero Gamma Level (where GEX crosses from negative to positive, if possible)
    # In VN market, it might stay negative. We look for the 'inflection' or 'flip'.
    zero_gamma_level = None
    for i in range(len(profile_df) - 1):
        if (profile_df.iloc[i]['total_gex'] * profile_df.iloc[i+1]['total_gex']) < 0:
            # Linear interpolation for zero point
            p1, g1 = profile_df.iloc[i]['price'], profile_df.iloc[i]['total_gex']
            p2, g2 = profile_df.iloc[i+1]['price'], profile_df.iloc[i+1]['total_gex']
            zero_gamma_level = p1 - g1 * (p2 - p1) / (g2 - g1)
            break
            
    return {
        "underlying": underlying_symbol,
        "current_price": base_price,
        "zero_gamma_level": zero_gamma_level,
        "profile": profile
    }

if __name__ == "__main__":
    # Test for HPG
    res = calculate_aggregate_gex("HPG")
    if "error" not in res:
        print(f"\n✅ Total Gamma Exposure for {res['underlying']}: {res['total_gex']:,.0f} VND per 1% move.")
        print("🧱 Top GEX Walls (Strike Levels):")
        for strike, val in res['walls'].items():
            print(f"   Strike {strike:,.0f}đ: {val:,.0f} VND exposure")
    else:
        print(f"❌ {res['error']}")
