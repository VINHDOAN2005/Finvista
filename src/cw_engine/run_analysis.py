# -*- coding: utf-8 -*-
"""
🚀 VN-QUANT: MINIMALIST COVERED WARRANT RUNNER & PIPELINE
======================================================
Automated data fetching, Greeks computation, investment scoring and CLI output.

Usage:
  python run_analysis.py --strategy balanced

Author: samvo
Version: 2.0 (Super Minimalist)
"""

import os
import sys
import json

# Disable vnstock analytics ads and silence standard notifications where possible
os.environ['VNSTOCK_SHOW_ADS'] = 'False'

# Pre-import vnstock at the very top so its background check messages print first
try:
    import vnstock
except ImportError:
    pass

import argparse
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from scipy.stats import norm

# Force stdout encoding to UTF-8 to handle Vietnamese text beautifully on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Import core pricing functions from our newly consolidated engine
try:
    from src.cw_engine.pricing_core import (
        calculate_greeks_for_cw,
        calculate_d1_d2,
        estimate_implied_volatility,
        score_cw,
        make_decision,
        parse_ratio,
        RISK_FREE_RATE,
        DEFAULT_VOLATILITY,
        fetch_dynamic_risk_free_rate
    )
except ImportError as e:
    print(f"❌ Core engine import failed: {e}. Please ensure src/cw_engine/pricing_core.py exists.")
    sys.exit(1)

# ==========================================
# 1. CORE DATA RETRIEVAL (VCI & VNSTOCK)
# ==========================================

def fetch_market_cw_data() -> pd.DataFrame:
    """Fetch live symbols, prices, ratios and strikes for all listed Vietnamese Warrants."""
    print("📡 Ingesting live Covered Warrant data from trading APIs...")
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Content-Type": "application/json",
        "Referer": "https://trading.vietcap.com.vn/quote"
    }
    
    symbols = []
    # Step 1: Fetch Symbol List with Retries
    url_list = "https://trading.vietcap.com.vn/api/price/symbols/getByGroup?group=CW"
    max_retries = 3
    backoff = 1.5
    for attempt in range(max_retries):
        try:
            resp = requests.get(url_list, headers=headers, timeout=10)
            if resp.status_code == 200:
                symbols = [item['symbol'] for item in resp.json()]
                break
            elif resp.status_code in [502, 503, 504, 429]:
                print(f"⚠️ Primary symbol registry returned {resp.status_code}. Retrying in {backoff}s... (Attempt {attempt+1}/{max_retries})")
                import time
                time.sleep(backoff)
                backoff *= 2
        except Exception:
            if attempt == max_retries - 1:
                break
            import time
            time.sleep(backoff)
            backoff *= 2

    # Step 2: Fetch details in batch (with retries if symbols fetched successfully)
    df = pd.DataFrame()
    if symbols:
        print(f"📥 Loading market details for {len(symbols)} warrant instruments...")
        url_details = "https://trading.vietcap.com.vn/api/price/symbols/getList"
        backoff = 1.5
        resp_details = None
        for attempt in range(max_retries):
            try:
                resp_details = requests.post(url_details, headers=headers, json={"symbols": symbols}, timeout=15)
                if resp_details.status_code == 200:
                    break
                elif resp_details.status_code in [502, 503, 504, 429]:
                    print(f"⚠️ Market details API returned {resp_details.status_code}. Retrying in {backoff}s... (Attempt {attempt+1}/{max_retries})")
                    import time
                    time.sleep(backoff)
                    backoff *= 2
            except Exception:
                if attempt == max_retries - 1:
                    break
                import time
                time.sleep(backoff)
                backoff *= 2
        
        rows = []
        if resp_details and resp_details.status_code == 200:
            for item in resp_details.json():
                listing = item.get('listingInfo', {})
                match = item.get('matchPrice', {})
                bidask = item.get('bidAsk', {})
                
                curr_price = float(match.get('matchPrice', 0) or listing.get('refPrice', 0) or 0)
                
                raw_val = float(match.get('accumulatedValue', 0) or 0)
                if raw_val > 0:
                    gtgd = raw_val
                else:
                    gtgd = (float(match.get('accumulatedVolume', 0) or 0) * curr_price) / 1e6
                
                rows.append({
                    'A_MaCW': listing.get('symbol'),
                    'B_MaCPCS': listing.get('underlyingSymbol'),
                    'C_GiaCW': curr_price,
                    'ref_price': float(match.get('referencePrice', 0) or listing.get('refPrice', 0) or 0),
                    'D_Volume': float(match.get('accumulatedVolume', 0) or 0),
                    'E_GTGD': gtgd,
                    'Q_DaoHan': listing.get('maturityDate'),
                    'R_Strike': float(listing.get('exercisePrice', 0) or 0),
                    'hidden_ratio': listing.get('exerciseRatio', '1:1'),
                    'issuer': listing.get('issuerName', ''),
                    'bid': float(bidask.get('bidPrices', [{}])[0].get('price', 0) or 0) if bidask.get('bidPrices') else 0,
                    'ask': float(bidask.get('askPrices', [{}])[0].get('price', 0) or 0) if bidask.get('askPrices') else 0,
                })
            df = pd.DataFrame(rows)

    # Fallback to local cache if live fetch failed completely
    cache_path = os.path.join("data", "excel_cw_report.csv")
    if df.empty:
        if os.path.exists(cache_path):
            print("\n⚠️ Live trading API is temporarily down (503 Service Unavailable).")
            print("🚀 Activating local offline cache fallback...")
            try:
                df = pd.read_csv(cache_path)
                print(f"💡 Successfully loaded {len(df)} warrants from cache ({cache_path})!")
                print("🖥️ Terminal running in OFFLINE mode with full pricing & Greeks simulator enabled!\n")
                
                # Ensure the critical columns exist in the cache df
                if 'hidden_underlying_price' not in df.columns:
                    df['hidden_underlying_price'] = df['ref_price']
                if 'O_Stock_FA' not in df.columns:
                    df['O_Stock_FA'] = 18.5
                return df
            except Exception as e:
                print(f"❌ Failed to parse local cache: {e}")
        else:
            print("❌ Live API down and no local offline cache found in data/excel_cw_report.csv.")
            return pd.DataFrame()

    # Step 3: Batch-fetch target underlying stock quotes (only if live succeeded)
    stocks = df['B_MaCPCS'].dropna().unique().tolist()
    if stocks:
        print(f"📥 Mapping last traded prices for {len(stocks)} underlying assets...")
        url_details = "https://trading.vietcap.com.vn/api/price/symbols/getList"
        resp_stocks = None
        for attempt in range(max_retries):
            try:
                resp_stocks = requests.post(url_details, headers=headers, json={"symbols": stocks}, timeout=10)
                if resp_stocks.status_code == 200:
                    break
                elif resp_stocks.status_code in [502, 503, 504, 429]:
                    import time
                    time.sleep(1)
            except Exception:
                pass
        
        if resp_stocks and resp_stocks.status_code == 200:
            p_map = {item['listingInfo']['symbol']: float(item['matchPrice'].get('matchPrice', 0) or 0) for item in resp_stocks.json()}
            df['hidden_underlying_price'] = df['B_MaCPCS'].map(p_map)
        else:
            print("⚠️ Failed underlying mapping. Reverting to reference prices.")
            df['hidden_underlying_price'] = df['ref_price']
            
    # Step 4: Map corporate credit health using the trained ML model
    try:
        import joblib
        from src.common import config
        distress_file = config.FINAL_DATASET_FILE
        model_dir = os.path.join("data", "financial_distress", "models")
        model_path = os.path.join(model_dir, "best_distress_model.pkl")
        scaler_path = os.path.join(model_dir, "scaler.pkl")
        
        if os.path.exists(distress_file) and os.path.exists(model_path) and os.path.exists(scaler_path):
            distress_df = pd.read_csv(distress_file)
            model = joblib.load(model_path)
            scaler = joblib.load(scaler_path)
            
            if not distress_df.empty:
                # Take the latest year's metrics per company
                latest_records = distress_df.sort_values('year').groupby('ticker').last().reset_index()
                
                # Exclude target and leakage features to align with the 32-feature trained model
                exclude_cols = {
                    "ticker", "company_name", "year", "exchange", "industry", 
                    "distress_label", "distress_label_next_year",
                    "ebit_to_interest", "icr", "current_ratio", "total_equity",
                    "springate_distressed", "zmijewski_distressed"
                }
                feature_cols = [c for c in latest_records.columns if c not in exclude_cols]
                
                prob_map = {}
                z_score_map = {}
                
                for idx, r in latest_records.iterrows():
                    ticker = r['ticker']
                    z_score_map[ticker] = float(r.get('altman_z_score', 3.0))
                    
                    try:
                        feat = r[feature_cols].to_frame().T.astype(float)
                        scaled = scaler.transform(feat)
                        # Re-create DataFrame to retain columns names to avoid LightGBM/XGBoost feature name warnings
                        scaled_df = pd.DataFrame(scaled, columns=feature_cols)
                        
                        # Use XGBoost / LightGBM proba
                        prob = float(model.predict_proba(scaled_df)[0, 1])
                        prob_map[ticker] = prob
                    except Exception:
                        prob_map[ticker] = 0.85 if r.get('distress_label') == 1 else 0.10
                
                df['underlying_distress_prob'] = df['B_MaCPCS'].map(prob_map).fillna(0.10)
                # Flag as distressed if ML probability is above threshold 50%
                df['underlying_is_distressed'] = df['underlying_distress_prob'].apply(lambda p: 1 if p >= 0.50 else 0)
                df['underlying_altman_z'] = df['B_MaCPCS'].map(z_score_map).fillna(3.0)
                
                # Integrate with existing fundamental score 'O_Stock_FA'
                def calculate_stock_fa(row):
                    ticker = row['B_MaCPCS']
                    prob = prob_map.get(ticker, 0.10)
                    z_score = z_score_map.get(ticker, 3.0)
                    if prob >= 0.50 or z_score < 1.1:
                        return 2.0  # Danger Red Zone! (ML Flags Distress)
                    elif z_score <= 2.6:
                        return 10.0  # Warning Grey Zone
                    else:
                        return 18.5  # Safe / Healthy Zone
                
                df['O_Stock_FA'] = df.apply(calculate_stock_fa, axis=1)
                print(f"📊 Integrated live ML credit risk check! Dynamic distress mapping complete for {len(prob_map)} underlying companies.")
            else:
                df['O_Stock_FA'] = 18.5
                df['underlying_is_distressed'] = 0
                df['underlying_distress_prob'] = 0.10
                df['underlying_altman_z'] = 3.0
        else:
            df['O_Stock_FA'] = 18.5
            df['underlying_is_distressed'] = 0
            df['underlying_distress_prob'] = 0.10
            df['underlying_altman_z'] = 3.0
    except Exception as e:
        df['O_Stock_FA'] = 15.0
        df['underlying_is_distressed'] = 0
        df['underlying_distress_prob'] = 0.10
        df['underlying_altman_z'] = 3.0


    return df

# ==========================================
# 2. ANALYTICS ENGINE INTEGRATION
# ==========================================

def fetch_underlying_historical_volatilities(symbols: list) -> dict:
    """
    Fetch daily historical price data using vnstock for the unique underlying symbols.
    Uses local JSON cache in `data/underlying_hv_cache.json` to prevent hitting vnstock rate limits.
    """
    hv_map = {}
    if not symbols:
        return hv_map
        
    cache_path = os.path.join("data", "underlying_hv_cache.json")
    
    # 1. Load existing cache if available
    cache = {}
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache = json.load(f)
        except Exception:
            pass
            
    # Default high-quality fallback HVs for Vietnam's top CW underlying assets
    defaults = {
        'ACB': 0.185, 'FPT': 0.331, 'HPG': 0.208, 'MBB': 0.187, 'MSN': 0.224,
        'MWG': 0.326, 'SHB': 0.236, 'STB': 0.406, 'TCB': 0.270, 'TPB': 0.199,
        'VHM': 0.587, 'VIB': 0.199, 'VIC': 0.484, 'VJC': 0.335, 'VNM': 0.153,
        'VPB': 0.281, 'VRE': 0.312, 'SSI': 0.295, 'HDB': 0.210, 'PLX': 0.220,
        'POW': 0.180, 'SAB': 0.160, 'CTG': 0.220
    }
    
    print("\n" + "=" * 75)
    print(f"📡 Resolving Historical Volatility (HV) for {len(symbols)} underlying assets...")
    print("=" * 75)
    
    now = datetime.now()
    end_date = now.strftime('%Y-%m-%d')
    start_date = (now - timedelta(days=90)).strftime('%Y-%m-%d')
    
    for sym in symbols:
        if not sym:
            continue
            
        # Check if cache has a fresh value (< 24 hours old)
        use_cache = False
        if sym in cache:
            try:
                cached_time = datetime.fromisoformat(cache[sym].get('timestamp', ''))
                if (now - cached_time).total_seconds() < 86400: # < 24 hours
                    hv_map[sym] = float(cache[sym]['hv'])
                    use_cache = True
            except Exception:
                pass
                
        if use_cache:
            print(f"   💾 {sym:<8} -> HV (Cached): {hv_map[sym]*100:6.2f}%")
            continue
            
        # Otherwise, attempt to fetch dynamically
        try:
            import time
            # Small throttle to respect the API limits
            time.sleep(0.5)
            
            quote = vnstock.Quote(symbol=sym)
            df = quote.history(start=start_date, end=end_date)
            if not df.empty and 'close' in df.columns:
                close = df['close']
                log_ret = np.log(close / close.shift(1)).dropna()
                if len(log_ret) >= 5:
                    std_dev = log_ret.tail(40).std()
                    hv = float(std_dev * np.sqrt(252))
                    hv_map[sym] = hv
                    cache[sym] = {
                        'hv': hv,
                        'timestamp': now.isoformat()
                    }
                    # Save cache immediately to disk to be resilient to process termination
                    try:
                        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
                        with open(cache_path, 'w', encoding='utf-8') as f:
                            json.dump(cache, f, ensure_ascii=False, indent=4)
                    except Exception:
                        pass
                    print(f"   📡 {sym:<8} -> HV (Fetch):  {hv*100:6.2f}%")
                    continue
        except (Exception, BaseException) as e:
            # Catch BaseException specifically to intercept vnstock's sys.exit() on rate-limit warnings
            pass
            
        # Fallback to cache (even if stale) or default
        if sym in cache:
            hv_map[sym] = float(cache[sym]['hv'])
            print(f"   ⚠️ {sym:<8} -> HV (Stale Cache): {hv_map[sym]*100:6.2f}%")
        else:
            hv_map[sym] = defaults.get(sym, 0.35)
            cache[sym] = {
                'hv': hv_map[sym],
                'timestamp': now.isoformat()
            }
            try:
                os.makedirs(os.path.dirname(cache_path), exist_ok=True)
                with open(cache_path, 'w', encoding='utf-8') as f:
                    json.dump(cache, f, ensure_ascii=False, indent=4)
            except Exception:
                pass
            print(f"   ⚠️ {sym:<8} -> HV (Fallback Default): {hv_map[sym]*100:6.2f}%")
            
    print("=" * 75 + "\n")
    return hv_map

def run_quant_calculations(df: pd.DataFrame, hv_map: dict) -> pd.DataFrame:
    """Inject Greeks, Implied Volatility, Historical Volatility, and Black-Scholes valuations."""
    if df.empty:
        return df
        
    res = df.copy()
    res['maturity_date_dt'] = pd.to_datetime(res['Q_DaoHan'], errors='coerce')
    res['days_to_expiry'] = (res['maturity_date_dt'] - pd.Timestamp.now()).dt.days
    res['L_Ngay'] = res['days_to_expiry']
    
    iv_list, delta_list, gamma_list, theta_list, vega_list, prob_list, theo_list, upside_list, theta_cw_list = [], [], [], [], [], [], [], [], []
    hv_list, iv_vs_hv_signal_list = [], []
    proj_3d_flat_list, proj_3d_up_list, proj_3d_down_list = [], [], []
    
    for idx, row in res.iterrows():
        try:
            S = float(row.get('hidden_underlying_price', 0) or 0)
            K = float(row.get('R_Strike', 0) or 0)
            days = float(row.get('days_to_expiry', 0) or 0)
            ratio = parse_ratio(row.get('hidden_ratio', '1:1'))
            m_price = float(row.get('C_GiaCW', 0) or 0)
            
            underlying_sym = row.get('B_MaCPCS')
            hv = hv_map.get(underlying_sym, 0.35)
            
            if S <= 0 or K <= 0 or days <= 0 or m_price <= 0:
                iv_list.append(0.3); delta_list.append(0.0); gamma_list.append(0.0); theta_list.append(0.0); vega_list.append(0.0); prob_list.append(0.0); theo_list.append(0.0); upside_list.append(0.0)
                theta_cw_list.append(0.0)
                hv_list.append(0.35); iv_vs_hv_signal_list.append('FAIR')
                proj_3d_flat_list.append(0.0); proj_3d_up_list.append(0.0); proj_3d_down_list.append(0.0)
                continue
                
            # 1. Back-solve for Implied Volatility (IV)
            iv = estimate_implied_volatility(m_price * ratio, S, K, int(days), RISK_FREE_RATE)
            
            # IV solver fallback: when CW trades at or below intrinsic value
            # (market_price < S-K), no sigma satisfies BSM. Use HV as proxy.
            if iv <= 0.015:
                iv = max(hv, 0.10)  # Use Historical Volatility, floor at 10%
            
            # 2. Compute Greeks adjusted for conversion ratio
            greeks = calculate_greeks_for_cw(S, K, int(days), iv, ratio, RISK_FREE_RATE)
            
            # 3. Compute Theoretical Fair Value (using default volatility proxy)
            T = days / 365.0
            d1, d2 = calculate_d1_d2(S, K, T, RISK_FREE_RATE, DEFAULT_VOLATILITY)
            theo_price = (S * norm.cdf(d1) - K * np.exp(-RISK_FREE_RATE * T) * norm.cdf(d2)) / ratio
            
            # 4. Volatility Arbitrage Signals
            if iv < hv - 0.05:
                vol_sig = 'CHEAP'
            elif iv > hv + 0.10:
                vol_sig = 'EXPENSIVE'
            else:
                vol_sig = 'FAIR'
                
            # 5. Compute 3-Day Projected Prices & Returns (T+3 Forecast under flat, bullish, bearish paths)
            days_3d = max(days - 3, 0)
            
            def get_proj_price(S_target):
                if days_3d <= 0 or S_target <= 0 or iv <= 0:
                    return max(S_target - K, 0.0) / ratio
                T_3d = days_3d / 365.0
                try:
                    d1_3d, d2_3d = calculate_d1_d2(S_target, K, T_3d, RISK_FREE_RATE, iv)
                    return (S_target * norm.cdf(d1_3d) - K * np.exp(-RISK_FREE_RATE * T_3d) * norm.cdf(d2_3d)) / ratio
                except Exception:
                    return max(S_target - K, 0.0) / ratio
                    
            p_flat = get_proj_price(S)
            p_up = get_proj_price(S * 1.02)     # +2% underlying movement
            p_down = get_proj_price(S * 0.98)   # -2% underlying movement
            
            ret_flat = (p_flat - m_price) / m_price * 100 if m_price > 0 else 0
            ret_up = (p_up - m_price) / m_price * 100 if m_price > 0 else 0
            ret_down = (p_down - m_price) / m_price * 100 if m_price > 0 else 0
            
            iv_list.append(iv)
            delta_list.append(greeks['delta'])
            gamma_list.append(greeks['gamma'])
            theta_list.append(greeks['theta'])
            vega_list.append(greeks['vega'])
            prob_list.append(greeks['prob_itm'])
            theo_list.append(theo_price)
            upside_list.append((theo_price - m_price) / m_price if m_price > 0 else 0)
            theta_cw_list.append(greeks['theta'] / ratio)
            hv_list.append(hv)
            iv_vs_hv_signal_list.append(vol_sig)
            
            proj_3d_flat_list.append(ret_flat)
            proj_3d_up_list.append(ret_up)
            proj_3d_down_list.append(ret_down)
            
        except Exception:
            iv_list.append(0.3); delta_list.append(0.0); gamma_list.append(0.0); theta_list.append(0.0); vega_list.append(0.0); prob_list.append(0.0); theo_list.append(0.0); upside_list.append(0.0); theta_cw_list.append(0.0)
            hv_list.append(0.35); iv_vs_hv_signal_list.append('FAIR')
            proj_3d_flat_list.append(0.0); proj_3d_up_list.append(0.0); proj_3d_down_list.append(0.0)
            
    res['S_IV_Pct'] = np.array(iv_list) * 100
    res['S_HV_Pct'] = np.array(hv_list) * 100
    res['IV_vs_HV_Signal'] = iv_vs_hv_signal_list
    res['T_Delta'] = delta_list
    res['T_Gamma'] = gamma_list
    res['T_Theta'] = theta_cw_list   # VND suy hao/ngày trên mỗi CW (đồng)
    res['T_Vega'] = vega_list
    res['prob_itm'] = prob_list
    res['theo_price'] = theo_list
    res['I_Upside'] = upside_list
    res['proj_3d_flat_pct'] = proj_3d_flat_list
    res['proj_3d_up_pct'] = proj_3d_up_list
    res['proj_3d_down_pct'] = proj_3d_down_list
    def _moneyness(r):
        S = float(r.get('hidden_underlying_price', 0) or 0)
        K = float(r.get('R_Strike', 0) or 0)
        if K <= 0 or S <= 0:
            return 'OTM'
        m = S / K
        if m < 0.85:
            return 'DEEP OTM'   # S lỗ > 15% so với Strike → Chắc chắn SKIP
        elif m < 0.98:
            return 'OTM'        # Lỗ nhẹ, đòn bẩy thô cao nhưng rủi ro
        elif m <= 1.02:
            return 'ATM'        # Vùng nổ Vol, Gamma max, nhạy sóng nhất
        elif m <= 1.15:
            return 'ITM'        # Đã có lãi, an toàn cho profile Balanced
        else:
            return 'DEEP ITM'   # Lãi sâu > 15%, Delta ~ 1, chạy như cổ phiếu cơ sở
    res['K_ITM_OTM'] = res.apply(_moneyness, axis=1)
    
    res['H_Loai'] = 'Call'
    res['M_GiaHL'] = res['R_Strike'] + (res['C_GiaCW'] * res['hidden_ratio'].apply(parse_ratio))
    res['J_HoaVon'] = res.apply(lambda r: (r['M_GiaHL'] - r['hidden_underlying_price'])/r['hidden_underlying_price'] if r.get('hidden_underlying_price', 0) > 0 else 0, axis=1)
    res['Premium_Pct'] = res['J_HoaVon'] * 100
    
    # 3 Cột nâng cấp khớp 100% với screenshot của "Họ" và được giải mã thuật toán tối ưu:
    res['price_change_pct'] = res.apply(lambda r: ((r['C_GiaCW'] - r['ref_price']) / r['ref_price'] * 100) if r['ref_price'] > 0 else 0, axis=1)
    res['intrinsic_value'] = res.apply(lambda r: max(0.0, (r['hidden_underlying_price'] - r['R_Strike']) / parse_ratio(r['hidden_ratio'])), axis=1)
    res['risk_monthly_pct'] = res.apply(lambda r: (r['Premium_Pct'] / (r['L_Ngay'] / 30.0)) if r['L_Ngay'] > 0 else 0, axis=1)
    
    # Calculate Gearing
    res['F_DonBay'] = res.apply(lambda r: (r['T_Delta'] * r['hidden_underlying_price'] / r['C_GiaCW']) if r['C_GiaCW'] > 0 and r.get('hidden_underlying_price', 0) > 0 else 0, axis=1)
    
    return res

def simulate_cw_scenarios(row):
    """
    Generate and print a 2D P/L Scenario Matrix for a specific Covered Warrant.
    X-axis: Underlying Stock price change (-10% to +10%)
    Y-axis: Time decay / Holding period (0 to 30 days)
    """
    symbol = row['A_MaCW']
    S = float(row.get('hidden_underlying_price', 0) or 0)
    K = float(row.get('R_Strike', 0) or 0)
    days_to_maturity = int(row.get('L_Ngay', 0) or 0)
    iv = float(row.get('S_IV_Pct', 45) or 45) / 100.0
    ratio = parse_ratio(row.get('hidden_ratio', '1:1'))
    current_price = float(row.get('C_GiaCW', 0) or 0)
    underlying_symbol = row['B_MaCPCS']
    
    if S <= 0 or current_price <= 0:
        print(f"❌ Invalid underlying price or warrant price for {symbol}.")
        return

    print("\n" + "=" * 125)
    print(f" 📊 VN-QUANT SCENARIO SIMULATOR: {symbol} (Underlying: {underlying_symbol})")
    print(f" Strike: {K:,.0f}đ | current Price: {current_price:,.0f}đ | IV: {iv*100:.2f}% | Days to Expiry: {days_to_maturity} days")
    print("=" * 125)
    print("📌 Expected P/L (%) based on holding period & stock price change (European Black-Scholes pricing):")
    print("=" * 125)
    
    # Scenarios
    price_changes = [-0.10, -0.05, -0.02, 0.00, 0.02, 0.05, 0.10]
    holding_days = [0, 5, 10, 20, 30]
    
    # Columns header
    headers = [f"{chg*100:+.0f}% ({S * (1+chg):,.0f}đ)" for chg in price_changes]
    print(f"{'Holding Period':<15} | " + " | ".join(f"{h:>14}" for h in headers))
    print("-" * 125)
    
    for hold in holding_days:
        if hold >= days_to_maturity:
            continue
            
        remaining_days = days_to_maturity - hold
        T_new = remaining_days / 365.0
        
        row_str = f"Sau {hold:<2} ngày"
        row_cells = []
        
        for chg in price_changes:
            S_new = S * (1 + chg)
            
            # Recalculate BSM
            d1, d2 = calculate_d1_d2(S_new, K, T_new, RISK_FREE_RATE, iv)
            theo_new = (S_new * norm.cdf(d1) - K * np.exp(-RISK_FREE_RATE * T_new) * norm.cdf(d2)) / ratio
            
            # P/L
            pl_pct = (theo_new - current_price) / current_price * 100
            
            # Format cell
            if pl_pct >= 0:
                cell_str = f"+{pl_pct:.1f}%"
            else:
                cell_str = f"{pl_pct:.1f}%"
                
            row_cells.append(f"{cell_str:>14}")
            
        print(f"{row_str:<15} | " + " | ".join(row_cells))
        
    print("=" * 125)
    print("💡 Tip: Holding period models Theta decay. +% Underlying represents positive Delta movement.")
    print("=" * 125 + "\n")

# ==========================================
# 3. PIPELINE CONTROL & MAIN BLOCK
# ==========================================

def silence_print_decorator(func):
    def wrapper(*args, **kwargs):
        import sys
        import builtins
        silent = '--silent' in sys.argv
        orig_print = builtins.print
        if silent:
            builtins.print = lambda *a, **k: None
        try:
            return func(*args, **kwargs)
        finally:
            builtins.print = orig_print
    return wrapper

@silence_print_decorator
def main():
    parser = argparse.ArgumentParser(description="VN-Quant Covered Warrant Minimalist Analyzer")
    parser.add_argument('--strategy', type=str, default='balanced', choices=['safe', 'balanced', 'aggressive'],
                        help="Scoring strategy (safe, balanced, aggressive)")
    parser.add_argument('--limit', type=int, default=15,
                        help="Number of rows to display in terminal")
    parser.add_argument('--all', action='store_true',
                        help="Display all covered warrants (overrides --limit)")
    parser.add_argument('--group-by', type=str, choices=['cpcs', 'tcph'], default=None,
                        help="Group and display warrants by underlying stock (cpcs) or issuer (tcph)")
    parser.add_argument('--simulate', type=str, default=None,
                        help="Warrant symbol to generate 2D P/L scenario matrix for (e.g. CACB2510)")
    parser.add_argument('--silent', action='store_true',
                        help="Silence terminal table printout completely")
    args = parser.parse_args()
    
    print("=" * 75)
    print(f" 🚀 VN-QUANT COVERED WARRANT TERMINAL PIPELINE (Profile: {args.strategy.upper()})")
    print("=" * 75)
    
    # 0. Fetch Dynamic Risk-Free Rate
    print("📡 Fetching dynamic risk-free rate (Vietnam 1Y Gov Bond Yield)...")
    dynamic_r = fetch_dynamic_risk_free_rate()
    global RISK_FREE_RATE
    RISK_FREE_RATE = dynamic_r
    
    from src.cw_engine import pricing_core
    pricing_core.RISK_FREE_RATE = dynamic_r
    print(f"📈 Risk-Free Rate successfully set to: {dynamic_r * 100:.3f}% (Continuous compounding)")
    print("=" * 75)
    
    # 1. Fetch raw data
    raw_df = fetch_market_cw_data()
    if raw_df.empty:
        print("❌ Ingestion yielded no results. Exiting.")
        return
        
    # 1.5. Fetch Underlying Historical Volatility
    underlyings = raw_df['B_MaCPCS'].dropna().unique().tolist()
    hv_map = fetch_underlying_historical_volatilities(underlyings)
        
    # 2. Run pricing calculations
    print("📈 Running Black-Scholes pricing models, Greeks and Newton-Raphson solvers...")
    calc_df = run_quant_calculations(raw_df, hv_map)
    
    # 3. Score and Decision
    print("🎯 Computing composite scores and evaluating risk limits...")
    final_df = score_cw(calc_df, strategy=args.strategy)
    final_df['U_Signal'] = final_df.apply(make_decision, axis=1)
    
    # Sort by score globally
    final_df = final_df.sort_values('G_Score', ascending=False)
    
    # Save CSV output
    os.makedirs('data', exist_ok=True)
    report_path = 'data/excel_cw_report.csv'
    final_df.to_csv(report_path, index=False)
    print(f"💾 Analysis complete! Full dataset exported successfully to {report_path}")
    
    # Synchronize with SQLite database
    save_opportunities_to_db(final_df)
    
    # Intercept for scenario simulation if --simulate is requested
    if args.simulate:
        symbol = args.simulate.upper().strip()
        match_rows = final_df[final_df['A_MaCW'] == symbol]
        if match_rows.empty:
            print(f"❌ Warrant symbol '{symbol}' not found in live market list. Please double check the symbol name.")
            return
        row = match_rows.iloc[0]
        simulate_cw_scenarios(row)
        return
    
    # Calculate market breadth metrics
    active_df = final_df[final_df['C_GiaCW'] > 0]
    up_cnt = len(active_df[active_df['C_GiaCW'] > active_df['ref_price']])
    down_cnt = len(active_df[active_df['C_GiaCW'] < active_df['ref_price']])
    flat_cnt = len(active_df[active_df['C_GiaCW'] == active_df['ref_price']])
    total_cnt = len(final_df)
    print("\n" + "=" * 110)
    print(" 📡 THỐNG KÊ TOÀN CẢNH ĐỘ RỘNG THỊ TRƯỜNG CHỨNG QUYỀN (Market Breadth)")
    print("=" * 110)
    print(f"  Tổng số mã quét: {total_cnt:<3} |  📈 Tăng giá: {up_cnt:<3} |  📉 Giảm giá: {down_cnt:<3} |  ➖ Tham chiếu: {flat_cnt:<3}")
    print("=" * 110)
    
    # Determine limits
    display_limit = len(final_df) if args.all else args.limit
    
    trading_cols = {
        'A_MaCW': 'Mã CW',
        'B_MaCPCS': 'Mã CPCS',
        'issuer': 'TCPH',
        'C_GiaCW': 'Giá CW',
        'price_change_pct': '+/- (%)',
        'intrinsic_value': 'Nội Tại',
        'M_GiaHL': 'Hòa Vốn',
        'Premium_Pct': 'Premium',
        'risk_monthly_pct': 'Độ Rủi Ro',
        'F_DonBay': 'Đòn Bẩy',
        'L_Ngay': 'Đáo Hạn',
        'G_Score': 'Điểm',
        'U_Signal': 'Khuyến Nghị'
    }
    
    quant_cols = {
        'A_MaCW': 'Mã CW',
        'B_MaCPCS': 'Mã CPCS',
        'hidden_underlying_price': 'Giá CPCS',
        'hidden_ratio': 'Tỷ Lệ',
        'R_Strike': 'Giá TH',
        'D_Volume': 'KLGD',
        'E_GTGD': 'GTGD',
        'S_IV_Pct': 'IV',
        'S_HV_Pct': 'HV',
        'T_Delta': 'Delta',
        'T_Theta': 'Θ/Ngày',
        'G_Score': 'Điểm',
        'U_Signal': 'Khuyến Nghị'
    }
    
    forecast_cols = {
        'A_MaCW': 'Mã CW',
        'B_MaCPCS': 'Mã CPCS',
        'C_GiaCW': 'Giá CW',
        'proj_3d_down_pct': 'T+3 Giảm (-2%)',
        'proj_3d_flat_pct': 'T+3 Đi Ngang (0%)',
        'proj_3d_up_pct': 'T+3 Tăng (+2%)',
        'U_Signal': 'Khuyến Nghị'
    }
    
    # Slice the top N warrants for display
    top_df = final_df.head(display_limit).copy()
    
    if args.group_by:
        group_col = 'B_MaCPCS' if args.group_by == 'cpcs' else 'issuer'
        group_label = 'CỔ PHIẾU CƠ SỞ (CPCS)' if args.group_by == 'cpcs' else 'NHÀ PHÁT HÀNH (TCPH)'
        
        print("\n" + "=" * 145)
        print(f" 🏆 VN-QUANT: PHÂN TÍCH NHÓM THEO {group_label}")
        print("=" * 145)
        
        # Group by and print
        grouped = top_df.groupby(group_col, sort=True)
        for g_name, g_df in grouped:
            if g_df.empty:
                continue
                
            clean_g_name = g_name if g_name else "Không xác định"
            print(f"\n📂 Nhóm: {clean_g_name} ({len(g_df)} mã cơ hội)")
            print("-" * 145)
            
            # --- BẢNG 1: THỰC CHIẾN ---
            print("📊 BẢNG 1: THỰC CHIẾN & TÍN HIỆU GIAO DỊCH (Trading View)")
            print("-" * 145)
            table1_df = g_df[list(trading_cols.keys())].copy()
            table1_df['C_GiaCW'] = table1_df['C_GiaCW'].map('{:,.0f}đ'.format)
            table1_df['price_change_pct'] = table1_df['price_change_pct'].map('{:+.1f}%'.format)
            table1_df['intrinsic_value'] = table1_df['intrinsic_value'].map('{:,.0f}đ'.format)
            table1_df['M_GiaHL'] = table1_df['M_GiaHL'].map('{:,.0f}'.format)
            table1_df['Premium_Pct'] = table1_df['Premium_Pct'].map('{:+.1f}%'.format)
            table1_df['risk_monthly_pct'] = table1_df['risk_monthly_pct'].map('{:+.2f}%'.format)
            table1_df['F_DonBay'] = table1_df['F_DonBay'].map('{:.1f}x'.format)
            table1_df['L_Ngay'] = table1_df['L_Ngay'].map('{:.0f}'.format)
            table1_df['G_Score'] = table1_df['G_Score'].map('{:.1f}'.format)
            
            table1_df = table1_df.rename(columns=trading_cols)
            if args.group_by == 'cpcs':
                table1_df = table1_df.drop(columns=['Mã CPCS'], errors='ignore')
            elif args.group_by == 'tcph':
                table1_df = table1_df.drop(columns=['TCPH'], errors='ignore')
            print(table1_df.to_string(index=False))
            print("-" * 145)
            
            # --- BẢNG 2: ĐỊNH LƯỢNG ---
            print("🔬 BẢNG 2: THÔNG SỐ ĐỊNH LƯỢNG & THAM CHIẾU CƠ BẢN (Quant View)")
            print("-" * 145)
            table2_df = g_df[list(quant_cols.keys())].copy()
            table2_df['hidden_underlying_price'] = table2_df['hidden_underlying_price'].map('{:,.0f}đ'.format)
            table2_df['R_Strike'] = table2_df['R_Strike'].map('{:,.0f}đ'.format)
            table2_df['D_Volume'] = table2_df['D_Volume'].map('{:,.0f}'.format)
            table2_df['E_GTGD'] = table2_df['E_GTGD'].map('{:,.1f}tr'.format)
            table2_df['S_IV_Pct'] = table2_df['S_IV_Pct'].map('{:.1f}%'.format)
            table2_df['S_HV_Pct'] = table2_df['S_HV_Pct'].map('{:.1f}%'.format)
            table2_df['T_Delta'] = table2_df['T_Delta'].map('{:.2f}'.format)
            table2_df['T_Theta'] = table2_df['T_Theta'].map(lambda x: f'{x:+.0f}đ' if x != 0 else '0đ')
            table2_df['G_Score'] = table2_df['G_Score'].map('{:.1f}'.format)
            
            table2_df = table2_df.rename(columns=quant_cols)
            if args.group_by == 'cpcs':
                table2_df = table2_df.drop(columns=['Mã CPCS', 'Giá CPCS'], errors='ignore')
            print(table2_df.to_string(index=False))
            print("-" * 145)

            # --- BẢNG 3: DỰ BÁO T+3 ---
            print("🔮 BẢNG 3: DỰ BÁO T+3 THỰC CHIẾN (T+3 Settlement Clearing Forecast)")
            print("-" * 145)
            table3_df = g_df[list(forecast_cols.keys())].copy()
            table3_df['C_GiaCW'] = table3_df['C_GiaCW'].map('{:,.0f}đ'.format)
            table3_df['proj_3d_down_pct'] = table3_df['proj_3d_down_pct'].map('{:+.1f}%'.format)
            table3_df['proj_3d_flat_pct'] = table3_df['proj_3d_flat_pct'].map('{:+.1f}%'.format)
            table3_df['proj_3d_up_pct'] = table3_df['proj_3d_up_pct'].map('{:+.1f}%'.format)
            
            table3_df = table3_df.rename(columns=forecast_cols)
            if args.group_by == 'cpcs':
                table3_df = table3_df.drop(columns=['Mã CPCS'], errors='ignore')
            print(table3_df.to_string(index=False))
            print("-" * 145)
            
    else:
        # Standard list representation
        print("\n" + "=" * 135)
        print(f" 🏆 TOP {display_limit} COVERED WARRANT OPPORTUNITIES (Vietnam Live Market)")
        print("=" * 135)
        
        # ----------------------------------------------------
        # BẢNG 1: THỰC CHIẾN & KHUYẾN NGHỊ (Trading View)
        # ----------------------------------------------------
        print("\n📊 BẢNG 1: THỰC CHIẾN & TÍN HIỆU GIAO DỊCH (Trading View)")
        print("-" * 135)
        table1_df = top_df[list(trading_cols.keys())].copy()
        table1_df['C_GiaCW'] = table1_df['C_GiaCW'].map('{:,.0f}đ'.format)
        table1_df['price_change_pct'] = table1_df['price_change_pct'].map('{:+.1f}%'.format)
        table1_df['intrinsic_value'] = table1_df['intrinsic_value'].map('{:,.0f}đ'.format)
        table1_df['M_GiaHL'] = table1_df['M_GiaHL'].map('{:,.0f}'.format)
        table1_df['Premium_Pct'] = table1_df['Premium_Pct'].map('{:+.1f}%'.format)
        table1_df['risk_monthly_pct'] = table1_df['risk_monthly_pct'].map('{:+.2f}%'.format)
        table1_df['F_DonBay'] = table1_df['F_DonBay'].map('{:.1f}x'.format)
        table1_df['L_Ngay'] = table1_df['L_Ngay'].map('{:.0f}'.format)
        table1_df['G_Score'] = table1_df['G_Score'].map('{:.1f}'.format)
        
        table1_df = table1_df.rename(columns=trading_cols)
        print(table1_df.to_string(index=False))
        print("-" * 135)
        
        # ----------------------------------------------------
        # BẢNG 2: THÔNG SỐ CƠ BẢN & ĐỊNH LƯỢNG (Quant View)
        # ----------------------------------------------------
        print("\n🔬 BẢNG 2: THÔNG SỐ ĐỊNH LƯỢNG & CƠ BẢN (Quant View)")
        print("-" * 135)
        table2_df = top_df[list(quant_cols.keys())].copy()
        table2_df['hidden_underlying_price'] = table2_df['hidden_underlying_price'].map('{:,.0f}đ'.format)
        table2_df['R_Strike'] = table2_df['R_Strike'].map('{:,.0f}đ'.format)
        table2_df['D_Volume'] = table2_df['D_Volume'].map('{:,.0f}'.format)
        table2_df['E_GTGD'] = table2_df['E_GTGD'].map('{:,.1f}tr'.format)
        table2_df['S_IV_Pct'] = table2_df['S_IV_Pct'].map('{:.1f}%'.format)
        table2_df['S_HV_Pct'] = table2_df['S_HV_Pct'].map('{:.1f}%'.format)
        table2_df['T_Delta'] = table2_df['T_Delta'].map('{:.2f}'.format)
        table2_df['T_Theta'] = table2_df['T_Theta'].map(lambda x: f'{x:+.0f}đ' if x != 0 else '0đ')
        table2_df['G_Score'] = table2_df['G_Score'].map('{:.1f}'.format)
        
        table2_df = table2_df.rename(columns=quant_cols)
        print(table2_df.to_string(index=False))
        print("=" * 135)

        # ----------------------------------------------------
        # BẢNG 3: DỰ BÁO T+3 THỰC CHIẾN (T+3 Settlement Clearing Forecast)
        # ----------------------------------------------------
        print("\n🔮 BẢNG 3: DỰ BÁO T+3 THỰC CHIẾN (T+3 Settlement Clearing Forecast)")
        print("-" * 135)
        table3_df = top_df[list(forecast_cols.keys())].copy()
        table3_df['C_GiaCW'] = table3_df['C_GiaCW'].map('{:,.0f}đ'.format)
        table3_df['proj_3d_down_pct'] = table3_df['proj_3d_down_pct'].map('{:+.1f}%'.format)
        table3_df['proj_3d_flat_pct'] = table3_df['proj_3d_flat_pct'].map('{:+.1f}%'.format)
        table3_df['proj_3d_up_pct'] = table3_df['proj_3d_up_pct'].map('{:+.1f}%'.format)
        
        table3_df = table3_df.rename(columns=forecast_cols)
        print(table3_df.to_string(index=False))
        print("=" * 135)
        
    # --- TELEGRAM WEBHOOK ALERTS ---
    try:
        from src.common.telegram_alerts import send_telegram_alert_batch, send_credit_distress_alert_batch
        strong_buys = final_df[final_df['U_Signal'] == 'STRONG BUY'].to_dict('records')
        near_expiry = final_df[(final_df['L_Ngay'] < 14) & (final_df['L_Ngay'] > 0)].to_dict('records')
        send_telegram_alert_batch(strong_buys, near_expiry)
        
        # Dispatch credit risk alerts for underlyings in Danger Zone
        distressed_warrants = final_df[final_df['underlying_is_distressed'] == 1]
        if not distressed_warrants.empty:
            unique_underlyings = distressed_warrants['B_MaCPCS'].unique()
            formatted_recs = []
            
            # Retrieve dynamic ML properties calculated during Step 4 mapping
            for ticker in unique_underlyings:
                match_row = distressed_warrants[distressed_warrants['B_MaCPCS'] == ticker].iloc[0]
                
                # Fetch actual live financial metrics from the latest record in final dataset
                # to build high-fidelity natural language commentary for the alert message
                from src.common import config
                distress_file = config.FINAL_DATASET_FILE
                c_ratio = 1.0
                d_ratio = 0.5
                pat_val = 0.0
                ocf_val = 0.0
                icr_val = 9999.0
                if os.path.exists(distress_file):
                    distress_df = pd.read_csv(distress_file)
                    latest_recs = distress_df[distress_df['ticker'] == ticker].sort_values('year')
                    if not latest_recs.empty:
                        last_row = latest_recs.iloc[-1]
                        c_ratio = float(last_row.get('current_ratio', 1.0))
                        d_ratio = float(last_row.get('debt_ratio', 0.5))
                        pat_val = float(last_row.get('profit_after_tax', 0.0))
                        ocf_val = float(last_row.get('operating_cash_flow', 0.0))
                        icr_val = float(last_row.get('ebit_to_interest', 9999.0))
                
                formatted_recs.append({
                    'ticker': ticker,
                    'altman_z_score': float(match_row.get('underlying_altman_z', 0.0)),
                    'xgboost_distress_probability': float(match_row.get('underlying_distress_prob', 0.0)),
                    'current_ratio': c_ratio,
                    'debt_ratio': d_ratio,
                    'profit_after_tax': pat_val,
                    'operating_cash_flow': ocf_val,
                    'ebit_to_interest': icr_val
                })
            send_credit_distress_alert_batch(formatted_recs)
    except Exception as e:
        import sys
        sys.stderr.write(f"\n⚠️ Failed to dispatch Telegram Webhook alerts: {e}\n")


def run_quant_pipeline_programmatic(strategy: str = 'balanced') -> pd.DataFrame:
    """
    Programmatic execution of the Covered Warrant pricing & credit health mapping pipeline.
    Returns the analyzed DataFrame, suitable for REST API integration.
    """
    dynamic_r = fetch_dynamic_risk_free_rate()
    from src.cw_engine import pricing_core
    pricing_core.RISK_FREE_RATE = dynamic_r
    
    raw_df = fetch_market_cw_data()
    if raw_df.empty:
        return pd.DataFrame()
        
    underlyings = raw_df['B_MaCPCS'].dropna().unique().tolist()
    hv_map = fetch_underlying_historical_volatilities(underlyings)
    calc_df = run_quant_calculations(raw_df, hv_map)
    
    final_df = score_cw(calc_df, strategy=strategy)
    final_df['U_Signal'] = final_df.apply(make_decision, axis=1)
    
    sorted_df = final_df.sort_values('G_Score', ascending=False)
    
    # Synchronize with SQLite database
    save_opportunities_to_db(sorted_df)
    
    return sorted_df

def save_opportunities_to_db(df: pd.DataFrame):
    """Persist quantitative scan results to SQLite Database (market_opportunities table)."""
    try:
        from src.common.database import SessionLocal, MarketOpportunity
        from datetime import datetime
        
        db = SessionLocal()
        try:
            # Clear existing table to perform full reload
            db.query(MarketOpportunity).delete()
            
            for _, row in df.iterrows():
                symbol = str(row.get('A_MaCW', '')).strip().upper()
                if not symbol:
                    continue
                
                opp = MarketOpportunity(
                    symbol=symbol,
                    underlying=row.get('B_MaCPCS'),
                    issuer=row.get('issuer'),
                    price=float(row.get('C_GiaCW', 0.0)) if pd.notna(row.get('C_GiaCW')) else None,
                    price_change_pct=float(row.get('price_change_pct', 0.0)) if pd.notna(row.get('price_change_pct')) else None,
                    intrinsic_value=float(row.get('intrinsic_value', 0.0)) if pd.notna(row.get('intrinsic_value')) else None,
                    break_even_price=float(row.get('M_GiaHL', 0.0)) if pd.notna(row.get('M_GiaHL')) else None,
                    premium_pct=float(row.get('Premium_Pct', 0.0)) if pd.notna(row.get('Premium_Pct')) else None,
                    risk_monthly_pct=float(row.get('risk_monthly_pct', 0.0)) if pd.notna(row.get('risk_monthly_pct')) else None,
                    gearing=float(row.get('F_DonBay', 0.0)) if pd.notna(row.get('F_DonBay')) else None,
                    days_to_maturity=int(row.get('L_Ngay', 0)) if pd.notna(row.get('L_Ngay')) else None,
                    score=float(row.get('G_Score', 0.0)) if pd.notna(row.get('G_Score')) else None,
                    decision_signal=row.get('U_Signal'),
                    
                    underlying_price=float(row.get('hidden_underlying_price', 0.0)) if pd.notna(row.get('hidden_underlying_price')) else None,
                    ratio=str(row.get('hidden_ratio', '1:1')),
                    strike_price=float(row.get('R_Strike', 0.0)) if pd.notna(row.get('R_Strike')) else None,
                    volume=float(row.get('D_Volume', 0.0)) if pd.notna(row.get('D_Volume')) else None,
                    turnover=float(row.get('E_GTGD', 0.0)) if pd.notna(row.get('E_GTGD')) else None,
                    implied_volatility_pct=float(row.get('S_IV_Pct', 0.0)) if pd.notna(row.get('S_IV_Pct')) else None,
                    historical_volatility_pct=float(row.get('S_HV_Pct', 0.0)) if pd.notna(row.get('S_HV_Pct')) else None,
                    delta=float(row.get('T_Delta', 0.0)) if pd.notna(row.get('T_Delta')) else None,
                    gamma=float(row.get('T_Gamma', 0.0)) if pd.notna(row.get('T_Gamma')) else None,
                    theta_burn_day=float(row.get('T_Theta', 0.0)) if pd.notna(row.get('T_Theta')) else None,
                    vega=float(row.get('T_Vega', 0.0)) if pd.notna(row.get('T_Vega')) else None,
                    prob_itm=float(row.get('prob_itm', 0.0)) if pd.notna(row.get('prob_itm')) else None,
                    theoretical_price=float(row.get('theo_price', 0.0)) if pd.notna(row.get('theo_price')) else None,
                    upside_pct=float(row.get('I_Upside', 0.0)) if pd.notna(row.get('I_Upside')) else None,
                    proj_3d_flat_pct=float(row.get('proj_3d_flat_pct', 0.0)) if pd.notna(row.get('proj_3d_flat_pct')) else None,
                    proj_3d_up_pct=float(row.get('proj_3d_up_pct', 0.0)) if pd.notna(row.get('proj_3d_up_pct')) else None,
                    proj_3d_down_pct=float(row.get('proj_3d_down_pct', 0.0)) if pd.notna(row.get('proj_3d_down_pct')) else None,
                    moneyness_category=row.get('K_ITM_OTM'),
                    
                    underlying_distress_prob=float(row.get('underlying_distress_prob', 0.0)) if pd.notna(row.get('underlying_distress_prob')) else None,
                    underlying_is_distressed=int(row.get('underlying_is_distressed', 0)) if pd.notna(row.get('underlying_is_distressed')) else None,
                    underlying_altman_z=float(row.get('underlying_altman_z', 3.0)) if pd.notna(row.get('underlying_altman_z')) else None,
                    last_updated=datetime.utcnow()
                )
                db.add(opp)
            db.commit()
            print("🚀 Successfully synchronized pricing opportunities to finvista.db!")
        except Exception as e:
            db.rollback()
            print(f"⚠️ Failed to save opportunities to SQLite: {e}")
        finally:
            db.close()
    except Exception as e:
         print(f"⚠️ Database import error in run_analysis: {e}")

if __name__ == "__main__":
    main()
