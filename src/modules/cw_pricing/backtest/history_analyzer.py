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
    from src.modules.cw_pricing.models.pricing_core import (
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

REPORT_PATH = os.path.join("data", "processed", "excel_cw_report.csv")

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
    
    # Step 1: Resolve metadata from database first (more reliable on cloud), fallback to CSV
    meta = None
    
    # Try database first
    try:
        from src.core.database import SessionLocal, MarketOpportunity
        db = SessionLocal()
        try:
            db_row = db.query(MarketOpportunity).filter(MarketOpportunity.symbol == cw_symbol).first()
            if db_row:
                # Map database fields to expected format
                meta = {
                    "B_MaCPCS": db_row.underlying,
                    "R_Strike": db_row.strike_price,
                    "hidden_ratio": db_row.ratio if db_row.ratio else "1:1",
                    "Q_DaoHan": (datetime.now() + timedelta(days=db_row.days_to_maturity)).strftime("%Y-%m-%d") if db_row.days_to_maturity else datetime.now().strftime("%Y-%m-%d")
                }
                print(f"✅ Found warrant metadata in database for {cw_symbol}")
        finally:
            db.close()
    except Exception as e:
        print(f"❌ Database lookup failed: {e}, trying CSV fallback...")
    
    # Fallback to CSV report if database didn't return data
    if meta is None and os.path.exists(REPORT_PATH):
        print(f"⚠️ Database lookup failed, trying CSV report fallback...")
        df = pd.read_csv(REPORT_PATH)
        match = df[df["A_MaCW"] == cw_symbol]
        if not match.empty:
            meta = match.iloc[0]
            print(f"✅ Found warrant metadata in CSV report for {cw_symbol}")
    
    if meta is None:
        print(f"❌ Warrant '{cw_symbol}' was not found in database or CSV report.")
        return pd.DataFrame()
        
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
    stock_hist = pd.DataFrame()
    try:
        stock_quote = vnstock.Quote(symbol=underlying_symbol)
        stock_hist = stock_quote.history(start=start_date_stock_str, end=end_date_str)
    except Exception as e:
        print(f"❌ Failed to fetch stock historical quotes: {e}")
        
    if stock_hist.empty or 'close' not in stock_hist.columns:
        print("⚠️ Stock historical quotes are empty or failed. Trying SQLite DB fallback...")
        try:
            from src.core.database import SessionLocal, StockHistoricalPrice
            db = SessionLocal()
            try:
                db_rows = db.query(StockHistoricalPrice).filter(
                    StockHistoricalPrice.symbol == underlying_symbol,
                    StockHistoricalPrice.date >= start_date_stock_str,
                    StockHistoricalPrice.date <= end_date_str
                ).order_by(StockHistoricalPrice.date).all()
                if db_rows:
                    stock_hist = pd.DataFrame([{
                        'date': r.date,
                        'open': r.open / 1000.0 if r.open is not None else None,
                        'high': r.high / 1000.0 if r.high is not None else None,
                        'low': r.low / 1000.0 if r.low is not None else None,
                        'close': r.close / 1000.0,  # Convert to thousands to match vnstock unit
                        'volume': r.volume
                    } for r in db_rows])
            finally:
                db.close()
        except Exception as dbe:
            print(f"❌ SQLite DB fallback failed for stock: {dbe}")

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
    # Try database first (more reliable on cloud environments)
    start_date_cw_dt = now - timedelta(days=lookback_days + 5)
    start_date_cw_str = start_date_cw_dt.strftime('%Y-%m-%d')
    print(f"📡 Retrieving historical quotes for warrant {cw_symbol} from {start_date_cw_str}...")
    cw_hist = pd.DataFrame()
    
    # Try vnstock API first to get real-time live data
    try:
        cw_quote = vnstock.Quote(symbol=cw_symbol)
        cw_hist = cw_quote.history(start=start_date_cw_str, end=end_date_str)
        if not cw_hist.empty and 'close' in cw_hist.columns:
            print(f"✅ Loaded data from vnstock API for {cw_symbol}")
    except Exception as e:
        print(f"❌ Failed to fetch warrant historical quotes from vnstock: {e}")
        
    # Fallback to database if vnstock API failed or returned empty
    if cw_hist.empty or 'close' not in cw_hist.columns:
        print(f"⚠️ vnstock API failed or returned empty, trying database fallback...")
        try:
            from src.core.database import SessionLocal, CWHistoricalPrice
            db = SessionLocal()
            try:
                db_rows = db.query(CWHistoricalPrice).filter(
                    CWHistoricalPrice.symbol == cw_symbol,
                    CWHistoricalPrice.date >= start_date_cw_str,
                    CWHistoricalPrice.date <= end_date_str
                ).order_by(CWHistoricalPrice.date).all()
                if db_rows:
                    cw_hist = pd.DataFrame([{
                        'date': r.date,
                        'open': r.open / 1000.0 if r.open is not None else None,
                        'high': r.high / 1000.0 if r.high is not None else None,
                        'low': r.low / 1000.0 if r.low is not None else None,
                        'close': r.close / 1000.0,  # Convert to thousands to match vnstock unit
                        'volume': r.volume
                    } for r in db_rows])
                    print(f"✅ Loaded {len(db_rows)} rows from database for {cw_symbol}")
            finally:
                db.close()
        except Exception as dbe:
            print(f"❌ Database fetch failed for warrant: {dbe}")

    if cw_hist.empty or 'close' not in cw_hist.columns:
        print("❌ Warrant historical quotes are empty.")
        print(f"⚠️ Returning empty DataFrame - this will cause 404 error in API")
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
    cols_to_keep = ['date', 'close', 'volume']
    for extra_col in ['open', 'high', 'low']:
        if extra_col in cw_hist.columns:
            cols_to_keep.append(extra_col)
            
    merged = pd.merge(
        cw_hist[cols_to_keep], 
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
    for col in ['open', 'high', 'low']:
        if col in merged.columns:
            merged[col] = merged[col] * VNSTOCK_PRICE_MULTIPLIER
    # Note: rolling_hv is computed from log returns (ratios), so it is unit-agnostic and needs no conversion
    
    # Step 5: Back-solve daily Implied Volatility (IV) and compute Greeks
    ivs, hvs, deltas, gearings, theta_burns = [], [], [], [], []
    theo_price_hvs, pricing_gap_pcts = [], []
    price_changes_stock, price_changes_cw = [], []
    
    from src.modules.cw_pricing.models.pricing_core import n_cdf, calculate_d1_d2
    import math
    
    for idx, row in merged.iterrows():
        trade_date = row['date']
        c_price = float(row['close_cw'])
        s_price = float(row['close_stock'])
        hv = float(row['rolling_hv'])
        
        # Calculate remaining calendar days to maturity on this trading date
        days_to_maturity = (maturity_date - trade_date).days
        days_to_maturity = max(1, days_to_maturity) # Safety floor
        T = days_to_maturity / 365.0
        
        # Solve for Implied Volatility (IV)
        iv = estimate_implied_volatility(
            market_price=c_price * ratio,
            underlying_price=s_price,
            strike_price=strike,
            days_to_maturity=days_to_maturity,
            risk_free_rate=RISK_FREE_RATE
        )
        
        # BSM-HV fair value & gap calculation
        calc_vol = hv if not np.isnan(hv) and hv > 0 else 0.35
        d1_hv, d2_hv = calculate_d1_d2(s_price, strike, T, RISK_FREE_RATE, calc_vol)
        theo_price_hv = (s_price * n_cdf(d1_hv) - strike * math.exp(-RISK_FREE_RATE * T) * n_cdf(d2_hv)) / ratio
        theo_price_hv = max(0.0, theo_price_hv)
        pricing_gap_pct = ((c_price - theo_price_hv) / theo_price_hv * 100) if theo_price_hv > 0 else 0.0
        
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
        theo_price_hvs.append(theo_price_hv)
        pricing_gap_pcts.append(pricing_gap_pct)
        
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
    merged['theo_price_hv'] = theo_price_hvs
    merged['pricing_gap_pct'] = pricing_gap_pcts
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
