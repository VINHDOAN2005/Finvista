# -*- coding: utf-8 -*-
"""
🏆 FINVISTA: INTRADAY TRADES SCRAPER & CVD GENERATOR
===================================================
Uses vnstock API to fetch intraday tick data.

Author: samvo
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Union
from vnstock import Quote

def get_ssi_trades(symbol: str) -> Union[pd.DataFrame, List[Dict[str, Any]]]:
    """
    Fetches intraday transaction ticks for a stock/covered warrant.
    """
    symbol = symbol.upper().strip()
    try:
        q = Quote(symbol=symbol)
        df = q.intraday(page_size=1000)
        if df is not None and not df.empty:
            return df
    except Exception as e:
        # Silently log/catch
        pass
    return pd.DataFrame()

def reconstruct_cvd(trades: Union[pd.DataFrame, List[Dict[str, Any]]]) -> dict:
    """
    Reconstructs Cumulative Volume Delta (CVD) stats.
    """
    if trades is None or (isinstance(trades, pd.DataFrame) and trades.empty) or (isinstance(trades, list) and not trades):
        return {"total_delta": 0, "delta_ratio": 0.0}

    if isinstance(trades, list):
        buy_vol = sum(t.get("volume", 0) for t in trades if str(t.get("match_type", "")).lower() == "buy")
        sell_vol = sum(t.get("volume", 0) for t in trades if str(t.get("match_type", "")).lower() == "sell")
    else: # pd.DataFrame
        # In case the columns might be slightly different or match_type has different casing
        if "match_type" in trades.columns:
            buy_vol = trades[trades["match_type"].str.lower() == "buy"]["volume"].sum()
            sell_vol = trades[trades["match_type"].str.lower() == "sell"]["volume"].sum()
        else:
            buy_vol = 0
            sell_vol = 0
            
    total_vol = buy_vol + sell_vol
    total_delta = buy_vol - sell_vol
    delta_ratio = float(total_delta / total_vol) if total_vol > 0 else 0.0

    return {
        "total_delta": int(total_delta),
        "delta_ratio": round(delta_ratio, 4)
    }
