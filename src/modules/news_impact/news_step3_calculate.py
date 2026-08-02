# -*- coding: utf-8 -*-
"""
📊 NEWS STEP 3: CALCULATE RETURNS AND ABNORMAL RETURNS (CAR)
============================================================
Calculates raw absolute returns and market-adjusted Cumulative Abnormal Returns (CAR)
over multiple horizons, and compiles the probabilities and stats.
"""

import numpy as np
import pandas as pd
from src.core.utils import logger

def calculate_forward_returns(
    aligned_events: list, 
    prices_map: dict, 
    market_returns: dict,
    horizons: list = [1, 3, 5, 10, 20]
) -> dict:
    """
    Compute forward absolute returns and Cumulative Abnormal Returns (CAR) for each aligned event.
    
    Returns:
        dict: {
            "event_returns": DataFrame with individual event returns,
            "horizon_stats": dict mapping horizon -> stats dict
        }
    """
    logger.info(f"🎬 [Step 3] Calculating raw returns and market-adjusted CAR for horizons {horizons}...")
    
    event_returns_data = []
    
    for event in aligned_events:
        sym = event["symbol"]
        df_prices = prices_map[sym]
        idx_0 = event["aligned_price_idx"]
        
        # Pre-news close as price reference
        ref_price = df_prices.iloc[idx_0 - 1]["close"] if idx_0 > 0 else df_prices.iloc[idx_0]["open"]
        if ref_price <= 0:
            continue
            
        returns_dict = {
            "id": event["id"],
            "symbol": sym,
            "category": event["category"],
            "title": event["title"],
            "news_date": event["news_date"],
            "aligned_date": event["aligned_date"],
            "ref_price": ref_price,
            "sentiment": event["sentiment"]
        }
        
        for h in horizons:
            idx_h = idx_0 + h - 1
            if idx_h < len(df_prices):
                price_h = df_prices.iloc[idx_h]["close"]
                
                # 1. Raw Return
                raw_ret = (price_h - ref_price) / ref_price
                returns_dict[f"return_{h}d"] = raw_ret
                
                # 2. Cumulative Market Return over the same trading dates
                comp_market_ret = 1.0
                for offset in range(h):
                    i_curr = idx_0 + offset
                    if i_curr < len(df_prices):
                        curr_date = df_prices.iloc[i_curr]["date"]
                        daily_mkt_ret = market_returns.get(curr_date, 0.0)
                        comp_market_ret *= (1.0 + daily_mkt_ret)
                comp_market_ret -= 1.0
                
                # 3. Cumulative Abnormal Return (CAR = Raw Return - Market Return)
                car_ret = raw_ret - comp_market_ret
                returns_dict[f"car_{h}d"] = car_ret
            else:
                returns_dict[f"return_{h}d"] = np.nan
                returns_dict[f"car_{h}d"] = np.nan
                
        event_returns_data.append(returns_dict)
        
    df_returns = pd.DataFrame(event_returns_data)
    if df_returns.empty:
        logger.warning("⚠️ No events had valid returns computed.")
        return {"event_returns": df_returns, "horizon_stats": {}}
        
    # Calculate stats per horizon
    horizon_stats = {}
    for h in horizons:
        raw_col = f"return_{h}d"
        car_col = f"car_{h}d"
        
        if raw_col not in df_returns.columns or car_col not in df_returns.columns:
            continue
            
        valid_raw = df_returns[raw_col].dropna()
        valid_car = df_returns[car_col].dropna()
        count = len(valid_raw)
        
        if count == 0:
            continue
            
        # Directional probabilities for CAR (Abnormal outperformance)
        car_up = valid_car[valid_car > 0.001]
        car_down = valid_car[valid_car < -0.001]
        car_flat = valid_car[(valid_car >= -0.001) & (valid_car <= 0.001)]
        
        p_up_car = len(car_up) / count
        p_down_car = len(car_down) / count
        p_flat_car = len(car_flat) / count
        
        # Group stats by sentiment (POSITIVE vs NEGATIVE vs NEUTRAL)
        sentiment_stats = {}
        for sent in ["POSITIVE", "NEGATIVE", "NEUTRAL"]:
            df_sent = df_returns[df_returns["sentiment"] == sent]
            if not df_sent.empty:
                sent_raw = df_sent[raw_col].dropna()
                sent_car = df_sent[car_col].dropna()
                if len(sent_raw) > 0:
                    sentiment_stats[sent] = {
                        "count": len(sent_raw),
                        "mean_raw": sent_raw.mean(),
                        "mean_car": sent_car.mean(),
                        "p_up_car": len(sent_car[sent_car > 0.001]) / len(sent_raw)
                    }
        
        horizon_stats[h] = {
            "count": count,
            # Raw returns stats
            "mean_raw": valid_raw.mean(),
            "std_raw": valid_raw.std() if count > 1 else 0.0,
            # CAR stats
            "p_up_car": p_up_car,
            "p_down_car": p_down_car,
            "p_flat_car": p_flat_car,
            "mean_car": valid_car.mean(),
            "median_car": valid_car.median(),
            "std_car": valid_car.std() if count > 1 else 0.0,
            "max_gain_car": valid_car.max(),
            "max_loss_car": valid_car.min(),
            "raw_car_list": valid_car.tolist(),
            "sentiment_stats": sentiment_stats
        }
        
    logger.info("✅ [Step 3] Raw returns and CAR metrics calculated successfully.")
    return {
        "event_returns": df_returns,
        "horizon_stats": horizon_stats
    }
