# -*- coding: utf-8 -*-
"""
🏆 FINVISTA: Covered Warrant Historical IV & Leverage Trend Analyzer
=====================================================================
Retrieves daily historical prices for both the Covered Warrant and its underlying stock.
Calculates historical rolling volatility (HV) and back-solves Implied Volatility (IV)
for every trading session over the last 20 business days to plot the volatility term structure.

Author: samvo
"""

import os
import sys
import json
import contextlib
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# Suppress vnstock promotional banners and deprecation warnings
with contextlib.redirect_stdout(open(os.devnull, 'w')), \
     contextlib.redirect_stderr(open(os.devnull, 'w')):
    import vnstock

try:
    from src.cw_engine.pricing_core import (
        estimate_implied_volatility,
        calculate_greeks_for_cw,
        parse_ratio,
        RISK_FREE_RATE
    )
except ImportError:
    # Local fallback imports if run directly
    from pricing_core import (
        estimate_implied_volatility,
        calculate_greeks_for_cw,
        parse_ratio,
        RISK_FREE_RATE
    )

REPORT_PATH = os.path.join("data", "excel_cw_report.csv")

def draw_ascii_chart(dates: list, ivs: list, hvs: list, title: str):
    """Draw a beautiful ASCII chart in the terminal comparing IV vs HV trends."""
    if not ivs:
        return
        
    print("\n📈 " + "=" * 80)
    print(f"  VOLATILITY HISTORICAL TREND CHART: {title} (IV vs HV)")
    print("  Legend:  * = Implied Volatility (IV)  |  # = Historical Volatility (HV)")
    print("=" * 80)
    
    # Scale variables
    max_val = max(max(ivs), max(hvs)) * 1.15
    min_val = min(min(ivs), min(hvs)) * 0.85
    
    # Ensure sane boundaries
    max_val = min(1.5, max(0.1, max_val))
    min_val = max(0.01, min_val)
    
    height = 10
    step = (max_val - min_val) / height
    
    for r in range(height, -1, -1):
        y_val = min_val + r * step
        line = f"  {y_val*100:5.1f}% | "
        
        for c in range(len(ivs)):
            iv_bin = int((ivs[c] - min_val) / step)
            hv_bin = int((hvs[c] - min_val) / step)
            
            if iv_bin == r and hv_bin == r:
                line += "@"  # Overlap
            elif iv_bin == r:
                line += "*"
            elif hv_bin == r:
                line += "#"
            else:
                line += " "
        print(line)
        
    print("        " + "-" * len(ivs))
    # Print X-axis dates (first, middle, last)
    date_labels = [d.strftime("%d/%m") for d in dates]
    x_axis = "         "
    for i, lbl in enumerate(date_labels):
        if i == 0 or i == len(dates) // 2 or i == len(dates) - 1:
            x_axis += lbl
        else:
            x_axis += " " * (len(lbl) - 1) if i < len(dates) - 1 else ""
    print(x_axis)
    print("=" * 80 + "\n")

def analyze_historical_warrant(cw_symbol: str, lookback_days: int = 20) -> pd.DataFrame:
    """
    Main function to orchestrate the retrieval, alignment, IV solving, and Greeks analysis
    for a Covered Warrant and its underlying asset over the last N business days.
    """
    cw_symbol = cw_symbol.upper().strip()
    
    # Step 1: Resolve metadata from our master report
    if not os.path.exists(REPORT_PATH):
        print(f"❌ Master analysis report not found at {REPORT_PATH}. Run python run_cw.py first!")
        return pd.DataFrame()
        
    df = pd.read_csv(REPORT_PATH)
    match = df[df["A_MaCW"] == cw_symbol]
    if match.empty:
        print(f"❌ Warrant '{cw_symbol}' was not found in the latest market scans.")
        return pd.DataFrame()
        
    meta = match.iloc[0]
    underlying_symbol = meta["B_MaCPCS"]
    strike = float(meta["R_Strike"])
    ratio_str = meta["hidden_ratio"]
    ratio = parse_ratio(ratio_str)
    maturity_date_str = meta["Q_DaoHan"]
    maturity_date = pd.to_datetime(maturity_date_str)
    
    print("\n" + "=" * 110)
    print(f" 🔬 RESEARCHING HISTORICAL IMPLIED VOLATILITY (IV) & EMPIRICAL LEVERAGE: {cw_symbol}")
    print(f"  Underlying Asset: {underlying_symbol} | Strike Price: {strike:,.0f}đ | Conversion Ratio: {ratio_str}")
    print(f"  Maturity Date:    {maturity_date.strftime('%Y-%m-%d')} | Continuous Risk-Free Rate: {RISK_FREE_RATE*100:.2f}%")
    print("=" * 110)
    
    # Step 2: Fetch longer stock history to calculate a rolling HV lookback correctly
    now = datetime.now()
    end_date_str = now.strftime('%Y-%m-%d')
    # Fetch 120 calendar days of historical stock data to get at least 40 business days lookback at start of lookback
    start_date_stock_dt = now - timedelta(days=lookback_days + 90)
    start_date_stock_str = start_date_stock_dt.strftime('%Y-%m-%d')
    
    print(f"📡 Retrieving historical quotes for stock {underlying_symbol} from {start_date_stock_str}...")
    try:
        stock_quote = vnstock.Quote(symbol=underlying_symbol)
        stock_hist = stock_quote.history(start=start_date_stock_str, end=end_date_str)
    except Exception as e:
        print(f"❌ Failed to fetch stock historical quotes: {e}")
        return pd.DataFrame()
        
    if stock_hist.empty or 'close' not in stock_hist.columns:
        print("❌ Stock historical quotes are empty.")
        return pd.DataFrame()
        
    # Standardize column names (vnstock returns 'time' in modern versions)
    if 'time' in stock_hist.columns and 'date' not in stock_hist.columns:
        stock_hist = stock_hist.rename(columns={'time': 'date'})
        
    # Standardize dates
    stock_hist['date'] = pd.to_datetime(stock_hist['date'])
    stock_hist = stock_hist.sort_values('date').reset_index(drop=True)
    
    # Calculate daily log returns
    stock_hist['log_return'] = np.log(stock_hist['close'] / stock_hist['close'].shift(1))
    
    # Calculate rolling 40-day Historical Volatility (HV)
    stock_hist['rolling_hv'] = stock_hist['log_return'].rolling(40).std() * np.sqrt(252)
    
    # Step 3: Fetch historical quotes for the Covered Warrant
    start_date_cw_dt = now - timedelta(days=lookback_days + 5)
    start_date_cw_str = start_date_cw_dt.strftime('%Y-%m-%d')
    print(f"📡 Retrieving historical quotes for warrant {cw_symbol} from {start_date_cw_str}...")
    try:
        cw_quote = vnstock.Quote(symbol=cw_symbol)
        cw_hist = cw_quote.history(start=start_date_cw_str, end=end_date_str)
    except Exception as e:
        print(f"❌ Failed to fetch warrant historical quotes: {e}")
        return pd.DataFrame()
        
    if cw_hist.empty or 'close' not in cw_hist.columns:
        print("❌ Warrant historical quotes are empty.")
        return pd.DataFrame()
        
    if 'time' in cw_hist.columns and 'date' not in cw_hist.columns:
        cw_hist = cw_hist.rename(columns={'time': 'date'})
        
    cw_hist['date'] = pd.to_datetime(cw_hist['date'])
    cw_hist = cw_hist.sort_values('date').reset_index(drop=True)
    
    # Normalize dates to date-only (remove intraday timestamps) to prevent duplicate rows
    stock_hist['date'] = stock_hist['date'].dt.normalize()
    cw_hist['date'] = cw_hist['date'].dt.normalize()
    
    # Deduplicate: keep only the LAST record per trading day (final closing price)
    stock_hist = stock_hist.drop_duplicates(subset='date', keep='last')
    cw_hist = cw_hist.drop_duplicates(subset='date', keep='last')
    
    # Step 4: Align dataframes by date
    merged = pd.merge(
        cw_hist[['date', 'close', 'volume']], 
        stock_hist[['date', 'close', 'rolling_hv']], 
        on='date', 
        suffixes=('_cw', '_stock')
    )
    
    if merged.empty:
        print("❌ Alignment failed. Dates of CW and stock historical quotes do not overlap.")
        return pd.DataFrame()
        
    # Limit to the requested lookback period
    merged = merged.tail(lookback_days).copy().reset_index(drop=True)
    
    # ====================================================================
    # CRITICAL: vnstock returns prices in "nghìn đồng" (thousands of VND)
    # e.g. ACB close=24.8 means 24,800 VND
    # But our report CSV (from VCI API) stores prices in actual VND
    # e.g. R_Strike=22500 means 22,500 VND
    # We MUST convert vnstock prices to VND to match the Strike price unit
    # ====================================================================
    VNSTOCK_PRICE_MULTIPLIER = 1000
    merged['close_cw'] = merged['close_cw'] * VNSTOCK_PRICE_MULTIPLIER
    merged['close_stock'] = merged['close_stock'] * VNSTOCK_PRICE_MULTIPLIER
    # Note: rolling_hv is computed from log returns (ratios), so it is unit-agnostic and needs no conversion
    
    # Step 5: Back-solve daily Implied Volatility (IV) and compute Greeks
    ivs, hvs, deltas, gearings, theta_burns = [], [], [], [], []
    price_changes_stock, price_changes_cw = [], []
    
    for idx, row in merged.iterrows():
        trade_date = row['date']
        c_price = float(row['close_cw'])
        s_price = float(row['close_stock'])
        hv = float(row['rolling_hv'])
        
        # Calculate remaining calendar days to maturity on this trading date
        days_to_maturity = (maturity_date - trade_date).days
        days_to_maturity = max(1, days_to_maturity) # Safety floor
        
        # Solve for Implied Volatility (IV)
        iv = estimate_implied_volatility(
            market_price=c_price * ratio,
            underlying_price=s_price,
            strike_price=strike,
            days_to_maturity=days_to_maturity,
            risk_free_rate=RISK_FREE_RATE
        )
        
        # Sanity guard: if IV solver hit boundary floors (sigma <= 0.01),
        # it means the market price exceeds BSM theoretical max at any reasonable vol.
        # This happens during extreme intraday spikes. Use previous day's IV as fallback.
        if iv <= 0.015 and len(ivs) > 0:
            iv = ivs[-1]  # Carry forward previous session's IV
        
        # Compute Greeks on this date
        greeks = calculate_greeks_for_cw(
            underlying_price=s_price,
            strike_price=strike,
            days_to_maturity=days_to_maturity,
            implied_volatility=iv,
            conversion_ratio=ratio,
            risk_free_rate=RISK_FREE_RATE
        )
        
        # Gearing
        gearing = (greeks['delta'] * s_price / c_price) if c_price > 0 else 0
        theta_burn = (abs(greeks['theta'] / ratio) / c_price) if c_price > 0 else 0
        
        ivs.append(iv)
        hvs.append(hv if not np.isnan(hv) else 0.35)
        deltas.append(greeks['delta'])
        gearings.append(gearing)
        theta_burns.append(theta_burn)
        
        # Calculate daily returns
        if idx > 0:
            prev_s = merged.loc[idx - 1, 'close_stock']
            prev_c = merged.loc[idx - 1, 'close_cw']
            chg_s = (s_price - prev_s) / prev_s * 100
            chg_c = (c_price - prev_c) / prev_c * 100
        else:
            chg_s = 0.0
            chg_c = 0.0
        price_changes_stock.append(chg_s)
        price_changes_cw.append(chg_c)
        
    merged['iv'] = ivs
    merged['hv'] = hvs
    merged['delta'] = deltas
    merged['gearing'] = gearings
    merged['theta_burn'] = theta_burns
    merged['chg_stock'] = price_changes_stock
    merged['chg_cw'] = price_changes_cw
    
    # Step 6: Print Table Report
    print("\n📊 HISTORICAL SESSIONS & BACK-SOLVED Greeks TIME-SERIES:")
    print("-" * 140)
    print(f"{'Ngày GD':<12} | {'Giá CP Cơ Sở':<18} | {'Giá CW':<16} | {'IV':>7} | {'HV':>7} | {'IV-HV Spread':>18} | {'Delta':>5} | {'Gearing':>7} | {'Θ Burn':>6}")
    print("-" * 120)
    
    for i, row in merged.iterrows():
        dt_str = row['date'].strftime("%Y-%m-%d")
        stock_str = f"{row['close_stock']:>7,.0f}đ ({row['chg_stock']:+.1f}%)"
        cw_str = f"{row['close_cw']:>5,.0f}đ ({row['chg_cw']:+.1f}%)"
        iv_val = row['iv']
        hv_val = row['hv']
        spread = iv_val - hv_val
        
        # Color-code the Vol Spread signal
        if spread < -0.05:
            vol_tag = "CHEAP"
        elif spread > 0.10:
            vol_tag = "EXPENSIVE"
        else:
            vol_tag = "FAIR"
        
        print(f"{dt_str:<12} | {stock_str:<18} | {cw_str:<16} | {iv_val*100:7.1f}% | {hv_val*100:7.1f}% | {spread*100:+6.1f}% {vol_tag:<9} | {row['delta']:5.3f} | {row['gearing']:6.1f}x | {row['theta_burn']*100:6.2f}%")
        
    print("-" * 140)
    
    # Summary statistics
    avg_iv = np.mean(merged['iv'])
    avg_hv = np.mean(merged['hv'])
    avg_spread = avg_iv - avg_hv
    avg_gearing = np.mean(merged['gearing'])
    print(f"\n  📈 Trung bình {lookback_days} phiên: IV={avg_iv*100:.1f}% | HV={avg_hv*100:.1f}% | Spread={avg_spread*100:+.1f}% | Gearing={avg_gearing:.1f}x")
    if avg_spread < -0.05:
        print("  💡 Nhận định: CW đang được định giá RẺ hơn biến động thực tế → Cơ hội mua Volatility Arbitrage!")
    elif avg_spread > 0.10:
        print("  ⚠️ Nhận định: CW đang bị thổi phồng IV quá cao → Nhà tạo lập đang hút tiền qua IV, cần thận trọng!")
    else:
        print("  ➖ Nhận định: IV và HV đang cân bằng hợp lý → Giá CW phản ánh đúng biến động thực tế.")
    
    # Step 7: Draw Chart
    draw_ascii_chart(
        dates=merged['date'].tolist(),
        ivs=merged['iv'].tolist(),
        hvs=merged['hv'].tolist(),
        title=cw_symbol
    )
    
    # Save historical run to data
    out_dir = os.path.join("data", "historical_research")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{cw_symbol}_iv_trend.csv")
    merged.to_csv(out_path, index=False)
    print(f"💾 Historical research logs successfully saved to {out_path}")
    
    return merged
