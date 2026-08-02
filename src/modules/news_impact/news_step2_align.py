# -*- coding: utf-8 -*-
"""
📊 NEWS STEP 2: ALIGN EVENTS AND COMPUTE MARKET INDEX
=====================================================
Aligns news events with historical trading prices and computes
an equal-weighted market index return proxy (from VN30 constituents) for CAPM adjustment.
"""

import pandas as pd
from sqlalchemy.orm import Session
from src.core.database import StockHistoricalPrice, CWHistoricalPrice, engine
from src.core.utils import logger

def fetch_historical_prices(db: Session, symbol: str) -> pd.DataFrame:
    """
    Fetch historical prices for a symbol. Checks stock_history first, then cw_history.
    """
    symbol_upper = symbol.upper().strip()
    
    # Optimize this query with read_sql as well
    try:
        df = pd.read_sql(
            "SELECT date, close, open, high, low, volume FROM stock_history "
            f"WHERE symbol = '{symbol_upper}' ORDER BY date ASC", 
            con=engine
        )
        if df.empty:
            df = pd.read_sql(
                "SELECT date, close, open, high, low, volume FROM cw_history "
                f"WHERE symbol = '{symbol_upper}' ORDER BY date ASC", 
                con=engine
            )
    except Exception as e:
        logger.debug(f"Failed to read symbol prices via pandas: {e}. Falling back.")
        df = pd.DataFrame()
        
    if df.empty:
        # Fallback to SQLAlchemy
        records = db.query(StockHistoricalPrice).filter(StockHistoricalPrice.symbol == symbol_upper).order_by(StockHistoricalPrice.date.asc()).all()
        if not records:
            records = db.query(CWHistoricalPrice).filter(CWHistoricalPrice.symbol == symbol_upper).order_by(CWHistoricalPrice.date.asc()).all()
        if not records:
            return pd.DataFrame()
        data = [{
            "date": pd.to_datetime(r.date).date(),
            "close": r.close,
            "open": r.open,
            "high": r.high,
            "low": r.low,
            "volume": r.volume
        } for r in records]
        df = pd.DataFrame(data)
    else:
        df["date"] = pd.to_datetime(df["date"]).dt.date
        
    return df.drop_duplicates(subset=["date"]).sort_values("date").reset_index(drop=True)

def compute_market_proxy_returns(db: Session) -> dict:
    """
    Computes an equal-weighted daily market return series using all available stocks.
    
    Returns:
        dict: mapping date -> market_return (float)
    """
    logger.info("📈 Computing VN30 Equal-Weighted Market Return Index Proxy...")
    
    try:
        # Fast query using pandas read_sql directly from engine
        df = pd.read_sql("SELECT date, symbol, close FROM stock_history ORDER BY date ASC", con=engine)
    except Exception as e:
        logger.warning(f"Failed to read from DB via pandas: {e}. Falling back to SQLAlchemy.")
        records = db.query(StockHistoricalPrice).order_by(StockHistoricalPrice.date.asc()).all()
        if not records:
            return {}
        df = pd.DataFrame([{
            "date": pd.to_datetime(r.date).date(),
            "symbol": r.symbol,
            "close": r.close
        } for r in records])
    
    if df.empty:
        return {}
        
    df["date"] = pd.to_datetime(df["date"]).dt.date
    
    # Pivot to get: index = date, columns = symbol, values = close
    df_pivot = df.pivot(index="date", columns="symbol", values="close")
    
    # Forward fill then backward fill missing prices
    df_pivot = df_pivot.ffill().bfill()
    
    # Calculate daily returns
    df_returns = df_pivot.pct_change()
    
    # Equal-weighted index daily returns (mean of returns across VN30 stocks)
    market_returns = df_returns.mean(axis=1)
    
    # Convert to dictionary mapping date -> return
    market_returns_dict = market_returns.dropna().to_dict()
    
    logger.info(f"✅ Market return index proxy computed for {len(market_returns_dict)} trading days.")
    return market_returns_dict

def align_events_to_prices(
    db: Session, 
    df_events: pd.DataFrame
) -> dict:
    """
    Align news events with price indexes, and compute market returns.
    
    Returns:
        dict: {
            "aligned_events": list of events,
            "prices_map": dict mapping symbol -> price DataFrame,
            "market_returns": dict mapping date -> market_return
        }
    """
    logger.info("🎬 [Step 2] Aligning news event timestamps and computing market proxy...")
    
    if df_events.empty:
        logger.warning("⚠️ Input events DataFrame is empty. Skipping alignment.")
        return {"aligned_events": [], "prices_map": {}, "market_returns": {}}
        
    unique_symbols = df_events["symbol"].unique()
    prices_map = {}
    
    logger.info(f"📊 Loading historical prices for {len(unique_symbols)} unique symbols...")
    for sym in unique_symbols:
        df_prices = fetch_historical_prices(db, sym)
        if not df_prices.empty:
            prices_map[sym] = df_prices
            
    # Compute market index returns
    market_returns = compute_market_proxy_returns(db)
            
    aligned_events = []
    for _, row in df_events.iterrows():
        sym = row["symbol"]
        if sym not in prices_map:
            continue
            
        df_prices = prices_map[sym]
        event_dt = row["date"]
        event_date = event_dt.date()
        
        target_date = event_date
        if event_dt.hour >= 15:
            target_date = event_date + pd.Timedelta(days=1)
            
        # Find first trading day on or after target_date
        matching_prices = df_prices[df_prices["date"] >= target_date]
        if matching_prices.empty:
            continue
            
        aligned_idx = matching_prices.index[0]
        aligned_row = matching_prices.iloc[0]
        
        aligned_events.append({
            "id": row["id"],
            "symbol": sym,
            "title": row["title"],
            "news_date": event_dt,
            "aligned_date": aligned_row["date"],
            "aligned_price_idx": aligned_idx,
            "aligned_close": aligned_row["close"],
            "category": row["category"],
            "sentiment": row["sentiment"]
        })
        
    logger.info(f"✅ [Step 2] Successfully aligned {len(aligned_events)} events with prices.")
    return {
        "aligned_events": aligned_events,
        "prices_map": prices_map,
        "market_returns": market_returns
    }
