# -*- coding: utf-8 -*-
"""
📊 NEWS STEP 4: STATISTICAL SIGNIFICANCE TESTING ON CAR
======================================================
Runs Welch's two-sample t-test comparing the Cumulative Abnormal Return (CAR)
distribution of news events against the baseline CAR distribution on non-event trading days.
"""

import numpy as np
import pandas as pd
from src.core.utils import logger

try:
    from scipy import stats
    scipy_available = True
except ImportError:
    stats = None
    scipy_available = False

def perform_significance_tests(
    df_returns: pd.DataFrame, 
    prices_map: dict, 
    market_returns: dict,
    horizon_stats: dict, 
    horizons: list = [1, 3, 5, 10, 20]
) -> dict:
    """
    Compare post-news CAR against non-event trading sessions' CAR (baseline)
    for each horizon, and update the statistics with p-values.
    """
    logger.info("🎬 [Step 4] Running statistical significance tests (T-test) on CAR...")
    
    if df_returns.empty or not horizon_stats:
        logger.warning("⚠️ Empty returns data. Skipping significance tests.")
        return horizon_stats
        
    for h in horizons:
        if h not in horizon_stats:
            continue
            
        event_cars = [r for r in horizon_stats[h]["raw_car_list"] if not np.isnan(r)]
        if len(event_cars) < 2:
            horizon_stats[h]["t_stat"] = 0.0
            horizon_stats[h]["p_value"] = 1.0
            continue
            
        # Collect baseline CARs across all symbols represented in the events
        baseline_cars = []
        
        for sym in df_returns["symbol"].unique():
            if sym not in prices_map:
                continue
                
            df_prices = prices_map[sym]
            n_prices = len(df_prices)
            if n_prices <= h:
                continue
                
            # Find news date indices to exclude from baseline
            sym_events = df_returns[df_returns["symbol"] == sym]
            event_indices = set()
            for _, ev in sym_events.iterrows():
                try:
                    ev_date = ev["aligned_date"]
                    match_idx = df_prices[df_prices["date"] == ev_date].index
                    if not match_idx.empty:
                        idx_val = match_idx[0]
                        for offset in range(-h, h + 1):
                            event_indices.add(idx_val + offset)
                except Exception:
                    continue
            
            closes = df_prices["close"].values
            opens = df_prices["open"].values
            
            import random
            possible_indices = [idx for idx in range(n_prices - h) if idx not in event_indices]
            if len(possible_indices) > 100:
                sampled_indices = random.sample(possible_indices, 100)
            else:
                sampled_indices = possible_indices
                
            for i in sampled_indices:
                # Base price
                base = closes[i - 1] if i > 0 else opens[i]
                if base > 0:
                    raw_ret = (closes[i + h - 1] - base) / base
                    
                    # Compute market return for baseline period
                    comp_market_ret = 1.0
                    for offset in range(h):
                        i_curr = i + offset
                        if i_curr < n_prices:
                            curr_date = df_prices.iloc[i_curr]["date"]
                            daily_mkt_ret = market_returns.get(curr_date, 0.0)
                            comp_market_ret *= (1.0 + daily_mkt_ret)
                    comp_market_ret -= 1.0
                    
                    # Baseline CAR
                    car_ret = raw_ret - comp_market_ret
                    baseline_cars.append(car_ret)
                    
        # Filter NaNs/Infs
        baseline_cars = [r for r in baseline_cars if not np.isnan(r) and not np.isinf(r)]
        
        if len(baseline_cars) < 5:
            baseline_cars = [0.0] * 10
            
        t_stat = 0.0
        p_val = 1.0
        
        use_scipy = scipy_available
        if use_scipy:
            try:
                res = stats.ttest_ind(event_cars, baseline_cars, equal_var=False, nan_policy='omit')
                t_stat = res.statistic
                p_val = res.pvalue
            except Exception as e:
                logger.debug(f"SciPy t-test failed for horizon {h}d: {e}. Falling back to manual.")
                use_scipy = False
                
        if not use_scipy:
            try:
                n1 = len(event_cars)
                n2 = len(baseline_cars)
                m1 = np.mean(event_cars)
                m2 = np.mean(baseline_cars)
                v1 = np.var(event_cars, ddof=1) if n1 > 1 else 0.0
                v2 = np.var(baseline_cars, ddof=1) if n2 > 1 else 0.0
                
                denom = np.sqrt((v1 / n1) + (v2 / n2))
                if denom > 0:
                    t_stat = (m1 - m2) / denom
                    p_val = 2.0 * (1.0 - stats_norm_cdf(abs(t_stat)))
            except Exception:
                pass
                
        if np.isnan(p_val):
            p_val = 1.0
        if np.isnan(t_stat):
            t_stat = 0.0
            
        horizon_stats[h]["t_stat"] = t_stat
        horizon_stats[h]["p_value"] = p_val
        horizon_stats[h]["baseline_car_mean"] = np.mean(baseline_cars) if baseline_cars else 0.0
        
    logger.info("✅ [Step 4] Significance testing on CAR completed.")
    return horizon_stats

def stats_norm_cdf(x):
    """Simple approximation of cumulative standard normal distribution."""
    p = 0.3275911
    a1 = 0.254829592
    a2 = -0.284496736
    a3 = 1.421413741
    a4 = -1.453152027
    a5 = 1.061405429
    sign = 1 if x >= 0 else -1
    x_abs = abs(x) / np.sqrt(2.0)
    t = 1.0 / (1.0 + p * x_abs)
    y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * np.exp(-x_abs * x_abs)
    return 0.5 * (1.0 + sign * y)
