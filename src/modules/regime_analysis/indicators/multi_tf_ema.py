# -*- coding: utf-8 -*-
"""
🏆 FINVISTA: MULTI-TIMEFRAME EMA MOMENTUM STATUS
================================================
Calculates EMA trend signals across multiple spans/timeframes.

Author: samvo
"""
import pandas as pd
import numpy as np

def get_multi_tf_status(symbol: str) -> dict:
    """
    Computes Momentum status based on EMAs of multiple timeframes.
    Returns:
      {
        "status": "BULLISH" | "BEARISH" | "NEUTRAL",
        "overall_score": float (0-100),
        "emas": dict of values
      }
    """
    symbol = symbol.upper().strip()
    # Query historical prices from stock_history or cw_history to calculate EMAs
    from src.core.database import engine
    
    # Try fetching from stock_history first, then cw_history
    query = f"SELECT date, close FROM stock_history WHERE symbol = '{symbol}' ORDER BY date ASC"
    try:
        df = pd.read_sql(query, engine)
    except Exception:
        df = pd.DataFrame()
        
    if df.empty:
        query = f"SELECT date, close FROM cw_history WHERE symbol = '{symbol}' ORDER BY date ASC"
        try:
            df = pd.read_sql(query, engine)
        except Exception:
            df = pd.DataFrame()
            
    if df.empty or len(df) < 5:
        # Fallback to neutral if no data
        return {
            "status": "NEUTRAL",
            "overall_score": 50.0,
            "emas": {}
        }
        
    closes = df["close"].values
    
    # Calculate simple EMAs
    def calculate_ema(prices, span):
        return pd.Series(prices).ewm(span=span, adjust=False).mean().values[-1]
        
    ema5 = calculate_ema(closes, 5)
    ema20 = calculate_ema(closes, 20) if len(closes) >= 20 else ema5
    ema50 = calculate_ema(closes, 50) if len(closes) >= 50 else ema20
    
    latest_price = closes[-1]
    
    # Simple rule-based score
    bullish_signals = 0
    total_signals = 3
    
    if latest_price > ema5:
        bullish_signals += 1
    if ema5 > ema20:
        bullish_signals += 1
    if ema20 > ema50:
        bullish_signals += 1
        
    score = (bullish_signals / total_signals) * 100.0
    
    if score >= 66.0:
        status = "BULLISH"
    elif score <= 33.0:
        status = "BEARISH"
    else:
        status = "NEUTRAL"
        
    return {
        "status": status,
        "overall_score": round(score, 1),
        "emas": {
            "latest": round(latest_price, 2),
            "ema5": round(ema5, 2),
            "ema20": round(ema20, 2),
            "ema50": round(ema50, 2)
        }
    }
