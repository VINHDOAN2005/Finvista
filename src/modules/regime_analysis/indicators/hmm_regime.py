# -*- coding: utf-8 -*-
"""
🏆 FINVISTA: HMM REGIME DETECTOR
=================================
Calculates the dynamic market regime for VNINDEX using a 4-state Hybrid HMM.
"""

import os
import sqlite3
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from src.modules.regime_analysis.portfolio.regime_model import prepare_vnindex_features, fit_vnindex_hmm

def calculate_vnindex_regime(days: int = 1250) -> dict:
    """
    Dynamically calculates the market regime based on recent VNINDEX history.
    """
    # 1. Fetch VNINDEX data
    db_path = os.path.join("data", "finvista.db")
    df = pd.DataFrame()
    
    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            query = f"SELECT date, open, high, low, close, volume FROM stock_history WHERE symbol = 'VNINDEX' ORDER BY date ASC"
            df = pd.read_sql(query, conn)
            conn.close()
        except Exception:
            pass

    if df.empty or len(df) < 100:
        try:
            # Fallback to vnstock first
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            from vnstock import Market
            market = Market()
            idx = market.index(symbol='VNINDEX')
            df_vn = idx.ohlcv(start=start_date, end=end_date, resolution='1D')
            if df_vn is not None and not df_vn.empty:
                df = df_vn.reset_index()
                time_col = 'time' if 'time' in df.columns else ('date' if 'date' in df.columns else df.columns[0])
                df = df.rename(columns={
                    time_col: 'date',
                    'open': 'open',
                    'high': 'high',
                    'low': 'low',
                    'close': 'close',
                    'volume': 'volume'
                })
        except Exception:
            pass

        if df.empty or len(df) < 100:
            try:
                # Fallback to yfinance
                df = yf.download("^VNINDEX", start=start_date, end=end_date, progress=False)
                df = df.reset_index()
                df = df.rename(columns={'Date': 'date', 'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'})
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
            except Exception:
                pass

    # Safe fallback if absolutely no data is found
    if df.empty or len(df) < 50:
        return {
            "regime": "BULLISH_VOL_EXPANSION",
            "confidence": 0.75,
            "bias": "LONG_CW",
            "state": 1,
            "description": "Safe default regime (Insufficient data)."
        }

    # 2. Process features and run HMM
    try:
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)
        df_feats = prepare_vnindex_features(df)
        
        hybrid_model, _ = fit_vnindex_hmm(df_feats)
        states = hybrid_model.predict(df_feats)
        probs = hybrid_model.predict_proba(df_feats)
        
        latest_state = int(states[-1])
        latest_prob = float(probs[-1, latest_state])
        
        # Mapping to regimes and biases
        # State 0: Bullish Low Vol
        # State 1: Bullish High Vol
        # State 2: Bearish Low Vol
        # State 3: Bearish High Vol (Crisis)
        regime_map = {
            0: "BULLISH_VOL_CONTRACTION",
            1: "BULLISH_VOL_EXPANSION",
            2: "BEARISH_VOL_CONTRACTION",
            3: "BEARISH_VOL_EXPANSION"
        }
        
        bias_map = {
            0: "LONG_CW",
            1: "LONG_CW",
            2: "CASH_ONLY",
            3: "CASH_ONLY"
        }
        
        desc_map = {
            0: "Thị trường tăng trưởng ổn định, biến động thấp.",
            1: "Thị trường tăng trưởng mạnh mẽ, biến động cao (Môi trường thuận lợi cho CW).",
            2: "Thị trường giảm điểm trong biên độ hẹp, biến động thấp.",
            3: "Thị trường giảm điểm mạnh, biến động cực đoan (Rủi ro đuôi béo)."
        }
        
        return {
            "regime": regime_map.get(latest_state, "BULLISH_VOL_EXPANSION"),
            "confidence": latest_prob,
            "bias": bias_map.get(latest_state, "LONG_CW"),
            "state": latest_state,
            "description": desc_map.get(latest_state, "Chế độ thị trường xác định bởi HMM.")
        }
        
    except Exception as e:
        return {
            "regime": "BULLISH_VOL_EXPANSION",
            "confidence": 0.50,
            "bias": "LONG_CW",
            "state": 1,
            "description": f"Fallback regime due to error: {str(e)}"
        }
