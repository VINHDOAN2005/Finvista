# -*- coding: utf-8 -*-
"""
📊 FINVISTA: MARKET-WIDE GEX REPORT
==================================
Scans all underlying assets with active Covered Warrants and generates
a summary report of Gamma Exposure, Walls, and Volatility Triggers.

Author: samvo
"""

import os
import sys
import pandas as pd
from tabulate import tabulate

# Ensure project root is on PYTHONPATH
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.modules.cw_pricing.models.gex_engine import calculate_aggregate_gex
from src.modules.cw_pricing.backtest.fetcher import fetch_market_cw_data
from src.core.utils import logger

def generate_full_market_gex_report():
    logger.info("🚀 Starting Full Market GEX Scan...")
    
    # 1. Get all unique underlying symbols that have active CWs
    cw_df = fetch_market_cw_data()
    if cw_df.empty:
        logger.error("❌ No active CW data found.")
        return
        
    underlying_symbols = sorted(cw_df['B_MaCPCS'].unique().tolist())
    logger.info(f"🔍 Found {len(underlying_symbols)} underlying assets with active CWs.")
    
    report_data = []
    
    for sym in underlying_symbols:
        try:
            res = calculate_aggregate_gex(sym)
            if "error" in res:
                continue
                
            total_gex = res['total_gex']
            # Volatility Trigger Logic: 
            # If GEX is strongly negative, it's an accelerator.
            # If GEX is positive, it's a dampener.
            status = "STABLE (Dampener)" if total_gex > 0 else "UNSTABLE (Accelerator)"
            if abs(total_gex) < 1000: status = "NEUTRAL"
            
            # Find the strongest wall
            top_wall_strike = 0
            top_wall_val = 0
            if res['walls']:
                top_wall_strike = list(res['walls'].keys())[0]
                top_wall_val = list(res['walls'].values())[0]
            
            report_data.append({
                "Ticker": sym,
                "Price": res['price'],
                "Total GEX (VND/1%)": f"{total_gex:,.0f}",
                "Status": status,
                "Major Wall": f"{top_wall_strike:,.0f}",
                "Wall Impact": f"{top_wall_val:,.0f}"
            })
        except Exception as e:
            logger.error(f"⚠️ Error scanning {sym}: {e}")

    # 2. Display Result
    df_report = pd.DataFrame(report_data)
    if df_report.empty:
        print("No GEX data could be calculated.")
        return
        
    print("\n" + "="*100)
    print("🏆 FINVISTA: MARKET GAMMA EXPOSURE (GEX) SUMMARY REPORT")
    print("="*100)
    print(tabulate(df_report, headers='keys', tablefmt='psql', showindex=False))
    print("="*100)
    print("💡 Status Guide:")
    print("   - STABLE (Dampener): Dealer is Long Gamma. Market tends to mean-revert.")
    print("   - UNSTABLE (Accelerator): Dealer is Short Gamma. Potential for Squeezes/Crashes.")
    print("="*100 + "\n")

if __name__ == "__main__":
    generate_full_market_gex_report()
