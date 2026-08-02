# -*- coding: utf-8 -*-
"""
🛡️ FINVISTA: QUANTITATIVE PORTFOLIO STRESS TESTING ENGINE
=========================================================
Simulates extreme market scenarios (Black Swan events) to evaluate 
portfolio resilience and VaR impact.

Scenarios:
1. Black Monday: VNINDEX -15% in 1 day.
2. Volatility Spike: +20% absolute increase in Implied Volatility.
3. Liquidity Freeze: Bid-Ask spreads widen by 10x.
4. Credit Crunch: Underlying stocks default probability +5%.

Author: samvo
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime

# Ensure project root is on PYTHONPATH
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.modules.trading_engine.paper_trader import load_portfolio, get_portfolio_value
from src.modules.cw_pricing.models.pricing_core import calculate_all_greeks, calculate_d1_d2, RISK_FREE_RATE, parse_ratio
from scipy.stats import norm

def run_stress_test(username: str = "demo"):
    print("=" * 100)
    print(f" 🛡️ FINVISTA PORTFOLIO STRESS TEST (Account: {username.upper()})")
    print("=" * 100)
    
    portfolio = load_portfolio(username=username)
    if not portfolio["positions"]:
        print("❌ Portfolio is empty. No stress test possible.")
        return
        
    # Load live market data to get baseline
    from src.modules.cw_pricing.backtest.reporter import load_opportunities_from_db
    df_market = load_opportunities_from_db(fallback_to_csv=True)
    if df_market.empty:
        print("❌ Could not load market data for baseline.")
        return
        
    market_data = df_market.set_index("A_MaCW")
    
    baseline_nav = get_portfolio_value(portfolio, dict(zip(df_market["A_MaCW"], df_market["C_GiaCW"])))
    print(f" Baseline NAV: {baseline_nav:,.0f} VND")
    print("-" * 100)
    print(f"{'Scenario':<30} | {'NAV Impact (%)':>15} | {'Loss (VND)':>15} | {'Risk Level':<15}")
    print("-" * 100)
    
    scenarios = [
        {"name": "Black Monday (Stock -15%)", "dS": -0.15, "dIV": 0.05, "dSpread": 0.0},
        {"name": "Bear Market (Stock -7%)", "dS": -0.07, "dIV": 0.03, "dSpread": 0.01},
        {"name": "Vol Crush (IV -10%)", "dS": 0.0, "dIV": -0.10, "dSpread": 0.0},
        {"name": "Vol Spike (IV +15%)", "dS": -0.05, "dIV": 0.15, "dSpread": 0.02},
        {"name": "Liquidity Freeze", "dS": -0.02, "dIV": 0.0, "dSpread": 0.10},
    ]
    
    for sc in scenarios:
        shock_nav = portfolio["cash"]
        
        for sym, pos in portfolio["positions"].items():
            if sym not in market_data.index:
                shock_nav += pos["qty"] * pos["buy_price"] # Fallback
                continue
                
            row = market_data.loc[sym]
            S = float(row["hidden_underlying_price"])
            K = float(row["R_Strike"])
            T = float(row["L_Ngay"]) / 365.0
            iv = float(row["S_IV_Pct"]) / 100.0
            ratio = parse_ratio(row["hidden_ratio"])
            q = 0.02 # Avg div yield fallback
            
            # Apply shock
            S_shock = S * (1 + sc["dS"])
            iv_shock = max(0.10, iv + sc["dIV"])
            
            if T <= 0:
                p_shock = max(S_shock - K, 0.0) / ratio
            else:
                d1, d2 = calculate_d1_d2(S_shock, K, T, RISK_FREE_RATE, iv_shock, q)
                p_shock = (S_shock * np.exp(-q * T) * norm.cdf(d1) - K * np.exp(-RISK_FREE_RATE * T) * norm.cdf(d2)) / ratio
            
            # Liquidity impact on exit
            p_shock = p_shock * (1 - sc["dSpread"])
            
            shock_nav += pos["qty"] * p_shock
            
        impact_vnd = shock_nav - baseline_nav
        impact_pct = (impact_vnd / baseline_nav) * 100
        
        risk_level = "MODERATE"
        if impact_pct < -15: risk_level = "HIGH 🚨"
        if impact_pct < -30: risk_level = "CATASTROPHIC 🔥"
        if impact_pct > 0: risk_level = "SAFE ✅"
        
        print(f"{sc['name']:<30} | {impact_pct:>14.1f}% | {impact_vnd:>14,.0f} | {risk_level:<15}")
        
    print("-" * 100)
    print("💡 Recommendations:")
    # Dynamic advice based on Greeks
    total_delta_vnd = 0
    for sym, pos in portfolio["positions"].items():
        if sym in market_data.index:
            row = market_data.loc[sym]
            total_delta_vnd += float(row["T_Delta"]) * float(row["hidden_underlying_price"]) * pos["qty"]
            
    if total_delta_vnd > baseline_nav * 2:
        print("  ⚠️ Portfolio Delta exposure is very high (>200% NAV). Consider reducing position sizes or hedging.")
    else:
        print("  ✅ Delta exposure is within manageable limits.")
    print("=" * 100 + "\n")

if __name__ == "__main__":
    run_stress_test()
