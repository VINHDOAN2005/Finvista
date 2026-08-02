# -*- coding: utf-8 -*-
"""
🏆 FINVISTA: COVERED WARRANT GRID SEARCH OPTIMIZATION
====================================================
Performs parameter sweep/tuning over combinations of:
- Stop Loss levels
- RSI Entry thresholds
- Trailing Stop thresholds
- ATR Multipliers
- Expiry early exits

Saves the optimal parameter configuration to JSON for trading engine integration.

Author: samvo
"""
import os
import sys
import json
import itertools
import warnings
import pandas as pd
import numpy as np
from src.core.database import engine

# Force terminal UTF-8 encoding on Windows to ensure flawless Vietnamese text rendering
if sys.platform == 'win32':
    import io
    if sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    if sys.stderr.encoding.lower() != 'utf-8':
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

warnings.filterwarnings('ignore')

# Pre-load price map and unique dates
print("📡 Pre-loading historical prices for optimization sweep...")
cw_prices_df = pd.read_sql("SELECT symbol, date, close FROM cw_history", engine)
cw_prices_df['date'] = pd.to_datetime(cw_prices_df['date']).dt.strftime('%Y-%m-%d')
GLOBAL_PRICE_MAP = cw_prices_df.set_index(['symbol', 'date'])['close'].to_dict()
GLOBAL_ALL_DATES = sorted(cw_prices_df['date'].unique().tolist())

from src.modules.cw_pricing.backtest.opt_cw_backtest_audit import calc_indicators, run_strategy, calculate_portfolio_performance, get_all_data

def main():
    print("=" * 90)
    print(" ⚙️ RUNNING COVERED WARRANT STRATEGY PARAMETER SWEEP (GRID SEARCH)")
    print("=" * 90)
    
    # 1. Fetch raw data
    raw_df = get_all_data()
    # 2. Calculate indicators
    df = calc_indicators(raw_df)
    
    # Ingest historical derivatives sentiment
    try:
        import vnstock
        from datetime import datetime, timedelta
        
        dates = pd.to_datetime(df['date']).sort_values()
        min_date = dates.iloc[0]
        max_date = dates.iloc[-1]
        
        start_date = (min_date - timedelta(days=45)).strftime('%Y-%m-%d')
        end_date = max_date.strftime('%Y-%m-%d')
        
        df_f1m = vnstock.Quote(symbol='VN30F1M').history(start=start_date, end=end_date)
        df_vn30 = vnstock.Quote(symbol='VN30').history(start=start_date, end=end_date)
        
        if not df_f1m.empty and not df_vn30.empty:
            for d in [df_f1m, df_vn30]:
                if 'time' in d.columns:
                    d.rename(columns={'time': 'date'}, inplace=True)
                d['date'] = pd.to_datetime(d['date'])
                
            merged_deriv = pd.merge(
                df_f1m[['date', 'close']], 
                df_vn30[['date', 'close']], 
                on='date', 
                suffixes=('_f1m', '_vn30')
            ).sort_values('date').reset_index(drop=True)
            
            merged_deriv['basis'] = merged_deriv['close_f1m'] - merged_deriv['close_vn30']
            
            window = min(20, len(merged_deriv))
            rolling_mean = merged_deriv['basis'].rolling(window).mean()
            rolling_std = merged_deriv['basis'].rolling(window).std().fillna(1.5).replace(0.0, 1.5)
            merged_deriv['basis_zscore'] = (merged_deriv['basis'] - rolling_mean) / rolling_std
            
            def get_sentiment(row):
                z = row['basis_zscore']
                b = row['basis']
                if pd.isna(z):
                    return 'NEUTRAL'
                if z <= -1.5 or b < -6.0:
                    return 'BEARISH'
                elif z >= 1.5 or b > 3.0:
                    return 'BULLISH'
                return 'NEUTRAL'
                
            merged_deriv['market_sentiment'] = merged_deriv.apply(get_sentiment, axis=1)
            
            # Merge back into main df
            df['date_dt'] = pd.to_datetime(df['date'])
            df = pd.merge(
                df, 
                merged_deriv[['date', 'market_sentiment', 'basis_zscore']], 
                left_on='date_dt', 
                right_on='date', 
                how='left',
                suffixes=('', '_deriv')
            )
            df.drop(columns=['date_dt', 'date_deriv'], errors='ignore', inplace=True)
            df['market_sentiment'] = df['market_sentiment'].fillna('NEUTRAL')
            df['basis_zscore'] = df['basis_zscore'].fillna(0.0)
    except Exception as e:
        df['market_sentiment'] = 'NEUTRAL'
        df['basis_zscore'] = 0.0
        
    df = df.dropna()
    
    # Load report to match eligible CWs
    cw_struct = pd.read_csv('data/processed/excel_cw_report.csv', encoding='utf-8')
    eligible_cw = cw_struct[(cw_struct['T_Delta'].abs() >= 0.25) & (cw_struct['K_ITM_OTM'].isin(['ITM', 'DEEP ITM', 'ATM']))]
    eligible_symbols = eligible_cw['A_MaCW'].tolist()
    
    df = df[df['cw_symbol'].isin(eligible_symbols)]
    df = pd.merge(df, cw_struct[['A_MaCW', 'T_Delta', 'F_DonBay', 'Premium_Pct', 'S_IV_Pct', 'maturity_date_dt']], 
                  left_on='cw_symbol', right_on='A_MaCW', how='inner')
    
    cw_groups = [g.sort_values('date').reset_index(drop=True) for _, g in df.groupby('cw_symbol') if len(g) >= 30]
    
    # Search grid configuration
    sl_levels = [0.80, 0.85, 0.90]
    rsi_thresholds = [35, 40, 45]
    trailing_act_pcts = [1.06, 1.08, 1.10]
    trailing_drop_pcts = [0.93, 0.95]
    atr_multipliers = [0.6, 0.8, 1.0, 1.2]
    min_days_expiry_exits = [0, 10, 15]
    
    print(f"🧪 Total search space: {len(sl_levels) * len(rsi_thresholds) * len(trailing_act_pcts) * len(trailing_drop_pcts) * len(atr_multipliers) * len(min_days_expiry_exits)} configurations.")
    print("⏳ Scanning parameter combinations for optimal Sharpe & Profit Factor...")
    
    best_sharpe = -999.0
    best_params = None
    
    combinations = list(itertools.product(sl_levels, rsi_thresholds, trailing_act_pcts, trailing_drop_pcts, atr_multipliers, min_days_expiry_exits))
    
    for (sl, rsi_th, trailing_act, trailing_drop, atr_mult, min_days_exp) in combinations:
        trades = run_strategy(
            cw_groups, 
            sl=sl, 
            rsi_th=rsi_th, 
            use_adaptive_cb=True,
            trailing_act_pct=trailing_act,
            trailing_drop_pct=trailing_drop,
            ema_col='EMA15',
            tp_pct=None,
            atr_multiplier=atr_mult,
            min_days_expiry_exit=min_days_exp
        )
        if len(trades) >= 5:
            perf = calculate_portfolio_performance(trades)
            if perf:
                sharpe = perf.get('sharpe', -999.0)
                win_rate = perf.get('win_rate', 0.0)
                pf = perf.get('profit_factor', 0.0)
                
                # Prioritize high Sharpe, high Win Rate, and solid Profit Factor
                if sharpe > best_sharpe and win_rate >= 50.0 and pf >= 1.0:
                    best_sharpe = sharpe
                    best_params = {
                        'sl': sl,
                        'rsi_th': rsi_th,
                        'trailing_act_pct': trailing_act,
                        'trailing_drop_pct': trailing_drop,
                        'atr_multiplier': atr_mult,
                        'min_days_expiry_exit': min_days_exp,
                        'sharpe': sharpe,
                        'win_rate': win_rate,
                        'profit_factor': pf
                    }
                    
    if best_params:
        print("\n" + "=" * 70)
        print("🏆 OPTIMAL PARAMETERS FOUND:")
        print("=" * 70)
        print(f"  • Hard Stop Loss        : -{(1-best_params['sl'])*100:.0f}%")
        print(f"  • RSI Trigger Threshold : < {best_params['rsi_th']}")
        print(f"  • Trailing Stop Activation: +{(best_params['trailing_act_pct']-1)*100:.0f}%")
        print(f"  • Trailing Stop Drop    : -{(1-best_params['trailing_drop_pct'])*100:.0f}% from peak")
        print(f"  • ATR Stop Multiplier   : {best_params['atr_multiplier']:.1f}x")
        print(f"  • Expiry Cut-off Exit   : < {best_params['min_days_expiry_exit']} days")
        print(f"  • Simulated Sharpe Ratio: {best_params['sharpe']:.3f}")
        print(f"  • Simulated Win Rate    : {best_params['win_rate']:.1f}%")
        print(f"  • Simulated Profit Factor: {best_params['profit_factor']:.2f}")
        
        # Save to config
        config_dir = "data/config"
        os.makedirs(config_dir, exist_ok=True)
        config_path = os.path.join(config_dir, "opt_cw_params.json")
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(best_params, f, indent=4)
        print(f"\n💾 Saved optimal configuration parameters to: {config_path}")
    else:
        print("❌ Grid search did not converge on a set of parameters with Win Rate >= 50%.")

if __name__ == "__main__":
    main()
