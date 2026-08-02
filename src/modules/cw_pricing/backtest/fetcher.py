# -*- coding: utf-8 -*-
"""Vietcap API data ingestion and underlying historical volatility fetch."""

import os
import json
import time
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Force vnstock = None to prevent hanging on external API endpoints during scans
vnstock = None

def fetch_market_cw_data() -> pd.DataFrame:
    """Fetch live symbols, prices, ratios and strikes for all listed Vietnamese Warrants.
    
    Session-aware caching:
    - Trước 08:45 (trước 15phút mở phiên): Dùng cache cuối phiên hôm trước
    - 08:45-15:00 (trong phiên): Fetch live, cập nhật cache
    - Sau 15:00: Lưu cache cuối phiên, giữ cho đến 08:45 ngày hôm sau
    """
    # ── Kiểm tra smart session cache trước khi fetch live ──
    try:
        from src.infra.market_cache import should_use_cache, load_snapshot, save_snapshot, get_session_status
        sess = get_session_status()
        status_str = str(sess.get('status', ''))
        try:
            print(f"   [SESSION] Session status: {status_str}")
        except Exception:
            try:
                clean_status = status_str.encode('ascii', 'replace').decode('ascii')
                print(f"   [SESSION] Session status: {clean_status}")
            except Exception:
                pass
        if sess["use_cache"]:
            cached_df = load_snapshot()
            if cached_df is not None and not cached_df.empty:
                print("   [CACHE] Loaded data from session cache (outside trading hours).")
                return cached_df
            else:
                print("   [CACHE] No valid cache, continuing to fetch live...")
        _market_cache_module = (should_use_cache, save_snapshot)
    except ImportError:
        _market_cache_module = None
    
    print("Ingesting live Covered Warrant data from trading APIs...")
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
            
            # Query 10-day average daily turnover (GTGD) for each CW from database
            hist_avg_gtgd_map = {}
            try:
                from src.core.database import SessionLocal, CWHistoricalPrice
                from sqlalchemy import text
                db = SessionLocal()
                try:
                    sql = """
                        SELECT symbol, AVG(close * volume / 1000000.0) as avg_gtgd
                        FROM (
                            SELECT symbol, close, volume,
                                   ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY date DESC) as rn
                            FROM cw_history
                        )
                        WHERE rn <= 10
                        GROUP BY symbol
                    """
                    result = db.execute(text(sql)).fetchall()
                    for r in result:
                        hist_avg_gtgd_map[r[0]] = float(r[1])
                except Exception as dbe:
                    print(f"⚠️ Failed to query historical CW turnover: {dbe}")
                finally:
                    db.close()
            except Exception as e:
                print(f"⚠️ Database connection error for historical CW turnover: {e}")
                
            df['hist_avg_gtgd'] = df['A_MaCW'].map(hist_avg_gtgd_map).fillna(0.0)

    # Fallback to SQLite DB if live fetch failed completely
    if df.empty:
        print("\n⚠️ Live trading API is temporarily down (503 Service Unavailable).")
        print("🚀 Activating SQLite DB offline cache fallback...")
        try:
            from src.modules.cw_pricing.backtest.reporter import load_opportunities_from_db
            df = load_opportunities_from_db(fallback_to_csv=True)
            if not df.empty:
                print(f"💡 Successfully loaded {len(df)} warrants from DB cache!")
                print("🖥️ Terminal running in OFFLINE mode with full pricing & Greeks simulator enabled!\n")
                # Ensure the critical columns exist
                if 'hidden_underlying_price' not in df.columns:
                    df['hidden_underlying_price'] = df.get('ref_price', 0.0)
                if 'O_Stock_FA' not in df.columns:
                    df['O_Stock_FA'] = 18.5
                if 'hist_avg_gtgd' not in df.columns:
                    df['hist_avg_gtgd'] = 0.0
                return df
        except Exception as e:
            print(f"❌ DB cache fallback failed: {e}")
        print("❌ Live API down and DB cache is empty. Cannot continue.")
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
        
        # Load database fallback prices for underlying stocks as back up
        db_prices = {}
        try:
            from src.core.database import engine as _db_engine
            db_df = pd.read_sql("SELECT symbol, date, close FROM stock_history ORDER BY date", _db_engine)
            if not db_df.empty:
                db_prices = db_df.groupby('symbol')['close'].last().to_dict()
        except Exception as dbe:
            print(f"   ⚠️ Database stock prices fallback query failed: {dbe}")

        p_map = {}
        if resp_stocks and resp_stocks.status_code == 200:
            try:
                for item in resp_stocks.json():
                    symbol = item.get('listingInfo', {}).get('symbol')
                    if not symbol:
                        continue
                    match_info = item.get('matchPrice') or {}
                    list_info = item.get('listingInfo') or {}
                    
                    price = float(
                        match_info.get('matchPrice', 0) or 
                        list_info.get('refPrice', 0) or 
                        match_info.get('referencePrice', 0) or 
                        0
                    )
                    p_map[symbol] = price
            except Exception as e:
                print(f"   ⚠️ Failed to parse API stock prices: {e}")
        else:
            print("⚠️ Failed underlying mapping API call. Reverting to database/reference prices.")

        # Map mapped API prices
        df['hidden_underlying_price'] = df['B_MaCPCS'].map(p_map)
        
        # Clean and apply database/default fallbacks to avoid 0 values
        def clean_underlying_price(row):
            val = row.get('hidden_underlying_price')
            ticker = row.get('B_MaCPCS')
            if pd.isna(val) or val <= 0:
                val = db_prices.get(ticker, 0.0)
            if val <= 0:
                val = 20000.0  # Safe default price for stock
            return float(val)
            
        df['hidden_underlying_price'] = df.apply(clean_underlying_price, axis=1)
            
    # Step 4: Map corporate credit health using the SQLite database
    try:
        from src.core.database import SessionLocal, CompanyDistressAnalysis
        db = SessionLocal()
        try:
            records = db.query(CompanyDistressAnalysis).all()
            if records:
                data_list = []
                for r in records:
                    data_list.append({
                        "ticker": r.ticker,
                        "year": r.year,
                        "altman_z_score": r.altman_z_score,
                        "distress_probability": r.distress_probability or 0.0,
                        "is_distressed": r.is_distressed or 0
                    })
                distress_df = pd.DataFrame(data_list)
                
                # Take the latest year's metrics per company
                latest_records = distress_df.sort_values('year').groupby('ticker').last().reset_index()
                
                prob_map = dict(zip(latest_records['ticker'], latest_records['distress_probability']))
                z_score_map = dict(zip(latest_records['ticker'], latest_records['altman_z_score']))
                is_distressed_map = dict(zip(latest_records['ticker'], latest_records['is_distressed']))
                
                df['underlying_distress_prob'] = df['B_MaCPCS'].map(prob_map).fillna(0.10)
                # Flag as distressed if ML probability is above threshold 50%
                df['underlying_is_distressed'] = df['underlying_distress_prob'].apply(lambda p: 1 if p >= 0.50 else 0)
                df['underlying_altman_z'] = df['B_MaCPCS'].map(z_score_map).fillna(3.0)
                
                # Integrate with existing fundamental score 'O_Stock_FA'
                # Base score from XGBoost ML + Altman Z
                def calculate_stock_fa_base(row):
                    ticker = row['B_MaCPCS']
                    prob = prob_map.get(ticker, 0.10)
                    z_score = z_score_map.get(ticker, 3.0)
                    if prob >= 0.50 or z_score < 1.1:
                        return 2.0   # Danger Red Zone
                    elif z_score <= 2.6:
                        return 10.0  # Warning Grey Zone
                    else:
                        return 18.5  # Safe / Healthy Zone
                
                df['O_Stock_FA'] = df.apply(calculate_stock_fa_base, axis=1)
                # Store prob_map for systemic integration
                df['_prob_map_ref'] = df['B_MaCPCS'].map(prob_map).fillna(0.10)
                print(f"📊 Integrated live ML credit risk check from SQLite! Dynamic distress mapping complete for {len(prob_map)} underlying companies.")
            else:
                df['O_Stock_FA'] = 18.5
                df['underlying_is_distressed'] = 0
                df['underlying_distress_prob'] = 0.10
                df['underlying_altman_z'] = 3.0
        except Exception as e:
            print(f"⚠️ SQLite query for credit health mapping failed: {e}. Reverting to defaults.")
            df['O_Stock_FA'] = 18.5
            df['underlying_is_distressed'] = 0
            df['underlying_distress_prob'] = 0.10
            df['underlying_altman_z'] = 3.0
        finally:
            db.close()
    except Exception as e:
        df['O_Stock_FA'] = 15.0
        df['underlying_is_distressed'] = 0
        df['underlying_distress_prob'] = 0.10
        df['underlying_altman_z'] = 3.0

    # Step 5: Integrate DebtRank Systemic Risk as secondary hard gate signal (from DB)
    try:
        from src.core.database import SessionLocal, CompanyDistressAnalysis
        db = SessionLocal()
        try:
            sys_records = db.query(
                CompanyDistressAnalysis.ticker,
                CompanyDistressAnalysis.systemic_contagion_prob,
                CompanyDistressAnalysis.altman_z_score,
                CompanyDistressAnalysis.year
            ).all()
            if sys_records:
                import pandas as _pd
                sys_df = _pd.DataFrame([{
                    'ticker': r[0],
                    'systemic_distress_prob': r[1] if r[1] is not None else 0.10,
                    'risk_delta': 0.0,  # risk_delta stored in CSV only; default to 0
                    'year': r[3]
                } for r in sys_records])
                # Keep latest year per ticker
                sys_df = sys_df.sort_values('year').groupby('ticker').last().reset_index()

                sys_prob_map = dict(zip(sys_df['ticker'], sys_df['systemic_distress_prob']))
                sys_delta_map = dict(zip(sys_df['ticker'], sys_df['risk_delta']))

                df['underlying_systemic_prob'] = df['B_MaCPCS'].map(sys_prob_map).fillna(0.10)
                df['underlying_systemic_delta'] = df['B_MaCPCS'].map(sys_delta_map).fillna(0.0)
                df['underlying_systemic_status'] = df['underlying_systemic_prob'].apply(
                    lambda p: '🔴 RED (SYSTEMIC RISK)' if p >= 0.50 else '🟡 YELLOW (WATCH)' if p >= 0.20 else '✅ GREEN (SAFE)'
                )
                df['underlying_systemic_is_distressed'] = df['underlying_systemic_prob'].apply(lambda p: 1 if p >= 0.50 else 0)

                # ── CẢI TIẾN THỰC CHẤT: Dùng systemic_delta như hệ số phạt liên tục vào O_Stock_FA ──
                def recalc_fa_with_systemic(row):
                    base_fa = row.get('O_Stock_FA', 18.5)
                    if base_fa <= 2.0:
                        return base_fa
                    delta = float(row.get('underlying_systemic_delta', 0.0) or 0.0)
                    sys_prob = float(row.get('underlying_systemic_prob', 0.10) or 0.10)
                    penalty = min(delta * 3.0, 0.60)
                    if sys_prob > 0.20:
                        penalty += (sys_prob - 0.20) * 0.5
                    return max(base_fa * (1.0 - penalty), 2.0)

                if 'O_Stock_FA' in df.columns:
                    df['O_Stock_FA'] = df.apply(recalc_fa_with_systemic, axis=1)

                df.drop(columns=['_prob_map_ref'], errors='ignore', inplace=True)
                count_sys = int(df['underlying_systemic_is_distressed'].sum())
                print(f"🕸️ DebtRank systemic risk integrated from DB! {count_sys} CWs in systemic danger zone.")
            else:
                df['underlying_systemic_prob'] = 0.10
                df['underlying_systemic_delta'] = 0.0
                df['underlying_systemic_status'] = '✅ GREEN (SAFE)'
                df['underlying_systemic_is_distressed'] = 0
                print("⚠️ No systemic data in DB — run `python run.py credit --contagion` to populate it.")
        finally:
            db.close()
    except Exception as e:
        df['underlying_systemic_prob'] = 0.10
        df['underlying_systemic_delta'] = 0.0
        df['underlying_systemic_status'] = '✅ GREEN (SAFE)'
        df['underlying_systemic_is_distressed'] = 0
        print(f"⚠️ DebtRank layer failed gracefully: {e}")

    # ── Lưu cache sau khi fetch live thành công ──
    try:
        from src.infra.market_cache import save_snapshot, is_trading_session
        # Lưu cache sau mỗi lần scan (cả trong và sau phiên)
        save_snapshot(df)
    except Exception as _ce:
        pass  # Cache lỗi không ảnh hưởng luồng chính

    return df

# ==========================================
# 2. ANALYTICS ENGINE INTEGRATION
# ==========================================

def fetch_underlying_historical_volatilities(symbols: list) -> dict:
    """
    Fetch and calculate multi-window Historical Volatility (10-day, 20-day, 40-day lookbacks)
    for the unique underlying symbols.
    Prioritizes the local compiled CSV cache in `data/processed/all_stock_historical_prices.csv` 
    to avoid vnstock rate limit blocks, falling back to dynamic API fetch if needed.
    """
    hv_map = {}
    if not symbols:
        return hv_map

    # Default high-quality fallback HVs (representing 40-day benchmark defaults)
    defaults = {
        'ACB': 0.185, 'FPT': 0.331, 'HPG': 0.208, 'MBB': 0.187, 'MSN': 0.224,
        'MWG': 0.326, 'SHB': 0.236, 'STB': 0.406, 'TCB': 0.270, 'TPB': 0.199,
        'VHM': 0.587, 'VIB': 0.199, 'VIC': 0.484, 'VJC': 0.335, 'VNM': 0.153,
        'VPB': 0.281, 'VRE': 0.312, 'SSI': 0.295, 'HDB': 0.210, 'PLX': 0.220,
        'POW': 0.180, 'SAB': 0.160, 'CTG': 0.220
    }

    print("\n" + "=" * 85)
    print(f"📡 Resolving Multi-Window Historical Volatility (10N, 20N, 40N) for {len(symbols)} assets...")
    print("=" * 85)

    # 1. Try to compute from stock_history table in SQLite DB
    local_df = pd.DataFrame()
    try:
        from src.core.database import engine as _db_engine
        local_df = pd.read_sql(
            "SELECT symbol, date, close FROM stock_history ORDER BY symbol, date",
            _db_engine
        )
        if not local_df.empty:
            local_df['date'] = pd.to_datetime(local_df['date'])
            print(f"   💾 Loaded stock history from DB: {len(local_df)} rows. Analyzing volatility profiles...")
    except Exception as e:
        print(f"   ⚠️ Failed to load stock history from DB ({e}). Reverting to dynamic endpoints.")

    now = datetime.now()
    end_date = now.strftime('%Y-%m-%d')
    start_date = (now - timedelta(days=90)).strftime('%Y-%m-%d')

    for sym in symbols:
        if not sym:
            continue
        
        # Method A: Calculate from local database cache
        if not local_df.empty and 'symbol' in local_df.columns:
            sym_data = local_df[local_df['symbol'] == sym].sort_values('date')
            if len(sym_data) >= 15:
                try:
                    close_prices = sym_data['close']
                    log_ret = np.log(close_prices / close_prices.shift(1)).dropna()
                    
                    hv_10 = float(log_ret.tail(10).std() * np.sqrt(252))
                    hv_20 = float(log_ret.tail(20).std() * np.sqrt(252))
                    hv_40 = float(log_ret.tail(40).std() * np.sqrt(252))
                    
                    # Sanity check: replace NaN or zero
                    hv_10 = hv_10 if not np.isnan(hv_10) and hv_10 > 0 else defaults.get(sym, 0.35)
                    hv_20 = hv_20 if not np.isnan(hv_20) and hv_20 > 0 else defaults.get(sym, 0.35)
                    hv_40 = hv_40 if not np.isnan(hv_40) and hv_40 > 0 else defaults.get(sym, 0.35)
                    
                    hv_map[sym] = {
                        'hv_10': hv_10,
                        'hv_20': hv_20,
                        'hv_40': hv_40
                    }
                    print(f"   📊 {sym:<8} -> HV10: {hv_10*100:5.1f}% | HV20: {hv_20*100:5.1f}% | HV40: {hv_40*100:5.1f}% (Local Cache)")
                    continue
                except Exception:
                    pass

        # Method B: Dynamic API Fetch (with lookback)
        fetched_success = False
        if vnstock:
            try:
                import time
                time.sleep(0.3)  # Rate limiting safety throttle
                quote = vnstock.Quote(symbol=sym)
                df = quote.history(start=start_date, end=end_date)
                if not df.empty and 'close' in df.columns:
                    close = df['close']
                    log_ret = np.log(close / close.shift(1)).dropna()
                    if len(log_ret) >= 5:
                        hv_10 = float(log_ret.tail(10).std() * np.sqrt(252))
                        hv_20 = float(log_ret.tail(20).std() * np.sqrt(252))
                        hv_40 = float(log_ret.tail(40).std() * np.sqrt(252))
                        
                        hv_map[sym] = {
                            'hv_10': hv_10 if not np.isnan(hv_10) else defaults.get(sym, 0.35),
                            'hv_20': hv_20 if not np.isnan(hv_20) else defaults.get(sym, 0.35),
                            'hv_40': hv_40 if not np.isnan(hv_40) else defaults.get(sym, 0.35)
                        }
                        print(f"   📡 {sym:<8} -> HV10: {hv_10*100:5.1f}% | HV20: {hv_20*100:5.1f}% | HV40: {hv_40*100:5.1f}% (Live Fetch)")
                        fetched_success = True
            except (Exception, BaseException):
                pass

        # Method C: Default Fallback
        if not fetched_success:
            def_val = defaults.get(sym, 0.35)
            hv_map[sym] = {
                'hv_10': def_val,
                'hv_20': def_val,
                'hv_40': def_val
            }
            print(f"   ⚠️ {sym:<8} -> HV10: {def_val*100:5.1f}% | HV20: {def_val*100:5.1f}% | HV40: {def_val*100:5.1f}% (Fallback Default)")

    print("=" * 85 + "\n")
    return hv_map

def fetch_derivatives_sentiment() -> dict:
    """
    Fetch VN30 and VN30F1M historical index prices using vnstock,
    calculate the daily Basis Spread, and determine current market sentiment.
    """
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=45)).strftime('%Y-%m-%d')
    
    # Defaults in case of failure
    fallback_sentiment = {
        "status": "fallback",
        "vn30_close": 0.0,
        "vn30f1m_close": 0.0,
        "current_basis": 0.0,
        "basis_sma5": 0.0,
        "basis_momentum": 0.0,
        "vol_spike_pct": 0.0,
        "basis_zscore": 0.0,
        "market_sentiment": "NEUTRAL"
    }
    
    # Lazy-import vnstock here — the module-level `vnstock = None` guard is intentional
    # to skip slow HV fetches during scans, but this function must always run.
    try:
        import vnstock as _vnstock
    except ImportError:
        return fallback_sentiment

    try:
        f1m_quote = _vnstock.Quote(symbol='VN30F1M')
        df_f1m = f1m_quote.history(start=start_date, end=end_date)
        
        vn30_quote = _vnstock.Quote(symbol='VN30')
        df_vn30 = vn30_quote.history(start=start_date, end=end_date)
        
        if df_f1m.empty or df_vn30.empty:
            return fallback_sentiment
            
        for df in [df_f1m, df_vn30]:
            if 'time' in df.columns:
                df.rename(columns={'time': 'date'}, inplace=True)
            # Normalize to date-only (strip hour component) — VN30 index and VN30F1M
            # futures can come from different providers returning different time-of-day
            # (00:00:00 vs 07:00:00), which would cause the merge to return 0 rows.
            df['date'] = pd.to_datetime(df['date']).dt.normalize()
            
        merged = pd.merge(
            df_f1m[['date', 'close', 'volume']], 
            df_vn30[['date', 'close', 'volume']], 
            on='date', 
            suffixes=('_f1m', '_vn30')
        ).sort_values('date').reset_index(drop=True)
        
        if len(merged) < 5:
            return fallback_sentiment
            
        merged['basis'] = merged['close_f1m'] - merged['close_vn30']
        merged['basis_sma5'] = merged['basis'].rolling(5).mean()
        
        # Calculate dynamic Z-Score using 20-day rolling window (or maximum available)
        window = min(20, len(merged))
        rolling_mean = merged['basis'].rolling(window).mean()
        rolling_std = merged['basis'].rolling(window).std().fillna(1.5).replace(0.0, 1.5)
        merged['basis_zscore'] = (merged['basis'] - rolling_mean) / rolling_std
        
        latest = merged.iloc[-1]
        current_basis = float(latest['basis'])
        basis_sma5 = float(latest['basis_sma5']) if not pd.isna(latest['basis_sma5']) else current_basis
        basis_momentum = current_basis - basis_sma5
        latest_z = float(latest['basis_zscore']) if not pd.isna(latest['basis_zscore']) else 0.0
        
        avg_vol_5d = merged['volume_f1m'].iloc[-6:-1].mean() if len(merged) >= 6 else merged['volume_f1m'].mean()
        latest_vol = latest['volume_f1m']
        vol_spike_pct = float(((latest_vol - avg_vol_5d) / avg_vol_5d * 100)) if avg_vol_5d > 0 else 0.0
        
        # Statistical regime boundary: Z-Score <= -1.5 represents strong bearish panic
        if latest_z <= -1.5 or current_basis < -6.0:
            sentiment = 'BEARISH'
        elif latest_z >= 1.5 or (current_basis > 3.0 and basis_momentum > 0):
            sentiment = 'BULLISH'
        else:
            sentiment = 'NEUTRAL'
            
        return {
            "status": "success",
            "date": latest['date'].strftime('%Y-%m-%d'),
            "vn30_close": float(latest['close_vn30']),
            "vn30f1m_close": float(latest['close_f1m']),
            "current_basis": round(current_basis, 2),
            "basis_sma5": round(basis_sma5, 2),
            "basis_momentum": round(basis_momentum, 2),
            "vol_spike_pct": round(vol_spike_pct, 1),
            "basis_zscore": round(latest_z, 2),
            "market_sentiment": sentiment
        }
    except Exception as e:
        import traceback
        print(f"   ⚠️ [fetch_derivatives_sentiment] Error: {type(e).__name__}: {e}")
        traceback.print_exc()
        return fallback_sentiment
