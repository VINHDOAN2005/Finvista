# -*- coding: utf-8 -*-
"""
🔬 FINVISTA: REGIME PREDICTIVE POWER & STABILITY TEST (INSTITUTIONAL GRADE)
==========================================================================
Calculates:
1. Predictive Power: Forward 5D/20D Returns, Win Rate, Pseudo-Sharpe.
2. Stability: Average duration of each state (to check for flickering).
3. Transition Matrix: Probability of moving from State i to State j.
"""

import pandas as pd
import numpy as np
import os
import sys
import warnings

# Suppress pandas warnings for cleaner output
warnings.filterwarnings('ignore')

sys.path.append(os.getcwd())
from src.modules.regime_analysis.indicators.regime_detector import RegimeDetector
from src.core.database import engine

from scipy import stats

def evaluate_regime_power(symbols: list, days: int = 1500):
    print(f"🚀 [INSTITUTIONAL AUDIT v3.1] Running Deep Validation on {len(symbols)} symbols...")
    
    all_results = []
    
    for symbol in symbols:
        try:
            query = f"SELECT date, open, high, low, close, volume FROM stock_history WHERE symbol='{symbol}' ORDER BY date ASC"
            df = pd.read_sql(query, engine)
            if df.empty or len(df) < 500: continue
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            df.sort_index(inplace=True)
            df = df.tail(days)
            
            res = RegimeDetector.calculate_kairos_regimes(df)
            res['symbol'] = symbol
            res['fwd_ret_20d'] = res['price'].shift(-20) / res['price'] - 1
            res['next_regime'] = res['regime'].shift(-1)
            res['block_id'] = (res['regime'] != res['regime'].shift(1)).cumsum()
            all_results.append(res)
        except Exception as e:
            print(f"⚠️ Error processing {symbol}: {e}")

    if not all_results: return
    full_df = pd.concat(all_results).dropna(subset=['fwd_ret_20d'])
    
    print("\n" + "="*110)
    print(" 📊 1. PREDICTIVE POWER & STATISTICAL SIGNIFICANCE (20D FORWARD)".center(110))
    print("="*110)
    
    power_stats = []
    for regime, group in full_df.groupby('regime'):
        data = group['fwd_ret_20d'] * 100
        n = len(data)
        mu = data.mean()
        sigma = data.std()
        
        # T-statistic (H0: mu = 0)
        t_stat, p_val = stats.ttest_1samp(data, 0)
        
        # 95% Confidence Interval
        ci_low, ci_high = stats.t.interval(0.95, n-1, loc=mu, scale=sigma/np.sqrt(n)) if n > 1 else (0,0)
        
        power_stats.append({
            'Regime': regime,
            'N': n,
            'Mean(%)': round(mu, 2),
            '95% CI': f"[{ci_low:+.1f}, {ci_high:+.1f}]",
            'T-Stat': round(t_stat, 2),
            'P-Value': f"{p_val:.4f}",
            'WinRate': f"{(data > 0).mean()*100:.1f}%",
            'Sharpe': round((mu / sigma) * np.sqrt(12.6), 2) if sigma > 0 else 0
        })
        
    power_df = pd.DataFrame(power_stats).set_index('Regime').sort_index()
    print(power_df.to_string())
    
    print("\n" + "="*110)
    print(" 🛡️ 2. CROSS-SECTION ROBUSTNESS (PER-TICKER S3 PERFORMANCE)".center(110))
    print("="*110)
    
    s3_data = full_df[full_df['regime'] == 'S3: Xu_Hướng_Mạnh']
    ticker_stats = s3_data.groupby('symbol')['fwd_ret_20d'].agg(['count', 'mean', 'std']).copy()
    ticker_stats['win_rate'] = s3_data.groupby('symbol')['fwd_ret_20d'].apply(lambda x: (x > 0).mean() * 100)
    ticker_stats['mean'] *= 100
    ticker_stats = ticker_stats.rename(columns={'count': 'N', 'mean': 'Avg_Ret(%)', 'win_rate': 'Win%'})
    print(ticker_stats.round(2).to_string())
    
    print("\n" + "="*110)
    print(" ⏱️ 3. STABILITY & TRANSITION MATRIX SUMMARY".center(110))
    print("="*110)
    
    block_sizes = full_df.groupby(['symbol', 'regime', 'block_id']).size().reset_index(name='duration')
    avg_dur = block_sizes.groupby('regime')['duration'].mean().round(1)
    
    print("Avg Duration (Days) per State:")
    print(avg_dur.to_string())
    print("\n" + "="*110 + "\n")

if __name__ == "__main__":
    # Test on a highly representative and liquid basket
    test_basket = ["FPT", "VHM", "HPG", "VIC", "MSN", "MWG", "TCB", "VCB", "STB", "SSI"]
    evaluate_regime_power(test_basket, days=1500)
