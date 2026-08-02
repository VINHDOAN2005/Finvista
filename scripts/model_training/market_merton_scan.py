# -*- coding: utf-8 -*-
"""
🔬 FINVISTA: MARKET STRESS TEST (MERTON STRUCTURAL RISK)
=======================================================
Scans all underlying tickers for covered warrants and evaluates 
their structural credit health using the Merton DD model.
"""

import pandas as pd
import numpy as np
from src.core.database import engine
from src.modules.credit_risk.models.merton_engine import calculate_merton_dd_realtime

def run_stress_test():
    print("="*90)
    print(" 🔬 FINVISTA: STRATEGIC MARKET STRESS TEST (MERTON DD SCAN)")
    print("="*90)
    
    # 1. Get tickers that have financial data
    query = """
        SELECT DISTINCT ticker as symbol, market_cap
        FROM company_financials
    """
    try:
        companies = pd.read_sql(query, engine)
        # Get latest prices for these tickers
        active_stocks = []
        for _, co in companies.iterrows():
            ticker = co['symbol']
            p_query = f"SELECT close FROM stock_history WHERE symbol = '{ticker}' ORDER BY date DESC LIMIT 1"
            p_df = pd.read_sql(p_query, engine)
            if not p_df.empty:
                active_stocks.append({'symbol': ticker, 'close': p_df['close'].iloc[0]})
        active_stocks = pd.DataFrame(active_stocks)
    except Exception as e:
        print(f"❌ Query error: {e}")
        return

    if active_stocks.empty:
        print("❌ No active stocks found for stress test.")
        return

    print(f"📡 Scanning {len(active_stocks)} underlying tickers for structural risk...")
    
    results = []
    for _, row in active_stocks.iterrows():
        ticker = row['symbol']
        price = row['close']
        
        merton = calculate_merton_dd_realtime(ticker, price)
        if merton.get('status') != 'insufficient_data' and merton.get('status') != 'error':
            results.append(merton)
            
    if not results:
        print("❌ Could not calculate Merton scores (Insufficient financial data in DB).")
        return
        
    res_df = pd.DataFrame(results).sort_values('merton_dd')
    
    print("\n" + "="*95)
    print(f"{'Ticker':<8} | {'Status':<12} | {'Merton DD':>10} | {'Prob Default':>12} | {'Debt (Bn)':>12} | {'MCap (Bn)':>12}")
    print("-" * 95)
    
    for _, r in res_df.iterrows():
        status_color = r['status']
        print(f"{r['ticker']:<8} | {status_color:<12} | {r['merton_dd']:>10.2f} | {r['merton_pd']*100:>11.2f}% | {r['debt_bn']:>12,.1f} | {r['market_cap_bn']:>12,.1f}")
    
    print("="*95)
    
    distressed = res_df[res_df['status'] == 'DISTRESSED']
    watch = res_df[res_df['status'] == 'WATCH']
    
    print(f"\n🚩 KẾT LUẬN:")
    print(f"   - Tổng mã quét: {len(res_df)}")
    print(f"   - 🔴 DISTRESSED (Báo động Đỏ): {len(distressed)}")
    print(f"   - 🟡 WATCH      (Cảnh báo Vàng): {len(watch)}")
    print(f"   - ✅ HEALTHY    (An toàn): {len(res_df) - len(distressed) - len(watch)}")
    
    if not distressed.empty:
        print(f"\n⚠️ CẢNH BÁO: Các mã {', '.join(distressed['ticker'].tolist())} có rủi ro cấu trúc cực cao.")
        print("   => Hệ thống sẽ tự động chặn (Hard Gate) tất cả chứng quyền liên quan đến các mã này.")

if __name__ == "__main__":
    run_stress_test()
