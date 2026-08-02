from __future__ import annotations
import os
import pandas as pd
import yfinance as yf

def fetch_prices(tickers, start: str, end: str) -> pd.DataFrame:
    if isinstance(tickers, str):
        tickers = [tickers]
        
    # Check what symbols are available in the local SQLite DB
    db_symbols = set()
    try:
        from src.core.database import engine
        from sqlalchemy import text
        with engine.connect() as conn:
            res = conn.execute(text("SELECT DISTINCT symbol FROM stock_history"))
            db_symbols = {row[0] for row in res}
    except Exception as e:
        print(f"⚠️ Could not read symbols from SQLite: {e}")
        
    sqlite_tickers = [t for t in tickers if t in db_symbols]
    yf_tickers = [t for t in tickers if t not in db_symbols]
    
    prices_list = []
    
    # 1. Fetch from SQLite if available
    if sqlite_tickers:
        try:
            from src.core.database import engine
            tickers_str = "', '".join(sqlite_tickers)
            query = f"""
                SELECT symbol, date, close 
                FROM stock_history 
                WHERE symbol IN ('{tickers_str}') 
                  AND date >= '{start}' 
                  AND date <= '{end}'
                ORDER BY date ASC
            """
            db_df = pd.read_sql(query, engine)
            if not db_df.empty:
                pivoted = db_df.pivot(index='date', columns='symbol', values='close')
                pivoted.index = pd.to_datetime(pivoted.index).normalize()
                prices_list.append(pivoted)
        except Exception as e:
            print(f"⚠️ Error reading prices from SQLite: {e}")
            
    # 2. Fetch from Yahoo Finance for remaining tickers
    if yf_tickers:
        try:
            df = yf.download(yf_tickers, start=start, end=end, auto_adjust=True, progress=False)
            if not df.empty:
                if isinstance(df.columns, pd.MultiIndex):
                    pivoted = df["Close"].copy()
                else:
                    pivoted = df[["Close"]].rename(columns={"Close": yf_tickers[0]})
                pivoted.index = pd.to_datetime(pivoted.index).normalize()
                if pivoted.index.tz is not None:
                    pivoted.index = pivoted.index.tz_localize(None)
                prices_list.append(pivoted)
        except Exception as e:
            print(f"⚠️ Error downloading from yfinance: {e}")
            
    if not prices_list:
        return pd.DataFrame()
        
    # Align and merge
    prices = pd.concat(prices_list, axis=1)
    prices = prices.sort_index().ffill().bfill().dropna(how="all")
    return prices.astype("float64")

def fetch_vnindex_data(start: str, end: str) -> pd.DataFrame:
    """
    Downloads VNINDEX history (Close and Volume) from vnstock for the date range.
    Falls back to VNINDEX in SQLite database if vnstock fails.
    """
    start_date = pd.to_datetime(start)
    end_date = pd.to_datetime(end)
    days_diff = (end_date - start_date).days
    count = max(100, days_diff + 200)
    
    start_str = start_date.strftime('%Y-%m-%d')
    end_str = end_date.strftime('%Y-%m-%d')
    
    # 1. Try vnstock first
    try:
        from vnstock import Market
        market = Market()
        idx = market.index(symbol='VNINDEX')
        df = idx.ohlcv(start=start_str, end=end_str, resolution='1D', count=count)
        if df is not None and not df.empty:
            time_col = 'time' if 'time' in df.columns else 'date'
            df = df.sort_values(time_col).reset_index(drop=True)
            df['date'] = pd.to_datetime(df[time_col]).dt.normalize()
            if df['date'].dt.tz is not None:
                df['date'] = df['date'].dt.tz_localize(None)
            df = df.set_index('date')
            return df[['close', 'volume']].astype(float)
    except Exception as e:
        print(f"⚠️ Failed to download VNINDEX from vnstock: {e}. Trying SQLite...")
        
    # 2. Fallback to SQLite stock_history table
    try:
        from src.core.database import engine
        query = f"""
            SELECT date, close, volume 
            FROM stock_history 
            WHERE symbol = 'VNINDEX' 
              AND date >= '{start_str}' 
              AND date <= '{end_str}'
            ORDER BY date ASC
        """
        df = pd.read_sql(query, engine)
        if not df.empty:
            df['date'] = pd.to_datetime(df['date']).dt.normalize()
            if df['date'].dt.tz is not None:
                df['date'] = df['date'].dt.tz_localize(None)
            df = df.set_index('date')
            return df[['close', 'volume']].astype(float)
    except Exception as db_e:
        print(f"⚠️ Failed to load VNINDEX from SQLite: {db_e}")
        
    return pd.DataFrame()

def fetch_macro_data(start: str, end: str) -> pd.DataFrame:
    """Fetches macro features: VIX (^VIX) and 10-Year Treasury Yield (^TNX)."""
    macro_tickers = ["^VIX", "^TNX"]
    df = yf.download(macro_tickers, start=start, end=end, auto_adjust=True, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        macro_df = df["Close"].copy()
    else:
        macro_df = df[["Close"]].rename(columns={"Close": macro_tickers[0]})
    
    macro_df = macro_df.rename(columns={"^VIX": "VIX", "^TNX": "US10Y"})
    macro_df = macro_df.sort_index().ffill().bfill().dropna(how="all")
    return macro_df.astype("float64")

