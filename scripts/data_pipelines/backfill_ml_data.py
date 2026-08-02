# -*- coding: utf-8 -*-
"""
🏆 FINVISTA: BACKFILL ML DATASET SIMULATOR
==========================================
Generates a massive historical dataset for Machine Learning by reverse-engineering 
Implied Volatility (IV) and Greeks (Delta, Gamma, Theta) for every historical day 
of every active Covered Warrant.

This creates the "Hybrid" feature set: combining historical market reality 
with Black-Scholes theoretical math.

Author: samvo
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime
import warnings

# Ensure project root is on PYTHONPATH
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.core.database import engine
from src.modules.cw_pricing.models.pricing_core import (
    estimate_implied_volatility, 
    calculate_greeks_for_cw, 
    calculate_d1_d2, 
    RISK_FREE_RATE,
    parse_ratio
)
from src.modules.regime_analysis.indicators.volatility_models import VolatilityModeler
from scipy.stats import norm

warnings.filterwarnings('ignore')

def main():
    print("=" * 80)
    print(" 🚀 FINVISTA: BACKFILL ML DATASET SIMULATOR")
    print("=" * 80)
    
    # 1. Load data
    print("📥 Loading CW and Stock historical data from SQLite...")
    cw_hist = pd.read_sql("SELECT * FROM cw_history", engine)
    stock_hist = pd.read_sql("SELECT * FROM stock_history", engine)
    mo_df = pd.read_sql("SELECT symbol, underlying, strike_price, ratio, days_to_maturity, last_updated FROM market_opportunities", engine)
    
    if cw_hist.empty or mo_df.empty:
        print("❌ Error: Need both cw_history and market_opportunities to backfill.")
        return
        
    print(f"   ✅ Found {len(cw_hist):,} CW history rows and {len(mo_df)} active CW profiles.")
    
    # Parse ratios
    mo_df['parsed_ratio'] = mo_df['ratio'].apply(parse_ratio)
    
    # Estimate maturity dates
    # maturity_date = last_updated.date() + days_to_maturity
    mo_df['last_updated'] = pd.to_datetime(mo_df['last_updated'])
    mo_df['maturity_date'] = mo_df.apply(lambda row: row['last_updated'] + pd.Timedelta(days=row['days_to_maturity']), axis=1)
    
    # 2. Build Underlying Historical Volatility / GARCH features
    print("\n📈 Pre-calculating EWMA/GARCH historical volatility for underlying stocks...")
    underlying_vols = {}
    for underlying in mo_df['underlying'].unique():
        sh = stock_hist[stock_hist['symbol'] == underlying].sort_values('date')
        if not sh.empty:
            sh['date'] = pd.to_datetime(sh['date'])
            sh = sh.set_index('date')
            returns = sh['close'].pct_change().dropna()
            
            # Calculate rolling 30-day historical volatility
            hist_vol = returns.rolling(window=30).std() * np.sqrt(252) * 100
            
            # Calculate EWMA variance (as a fast proxy for GARCH in historical series)
            ewma_var = VolatilityModeler.ewma_variance(returns)
            ewma_vol = np.sqrt(ewma_var) * np.sqrt(252) * 100
            
            vol_df = pd.DataFrame({
                'historical_volatility_pct': hist_vol,
                'garch_vol_forecast_pct': ewma_vol # Proxy
            })
            underlying_vols[underlying] = vol_df
            
    # 3. Process each historical day for each CW
    print("\n⚙️ Reverse-engineering Greeks and BSM prices (This will take a few minutes)...")
    
    backfill_data = []
    
    # Optimize by doing row iteration safely
    cw_hist['date'] = pd.to_datetime(cw_hist['date'])
    stock_hist['date'] = pd.to_datetime(stock_hist['date'])
    
    # Convert stock_hist to a fast lookup dictionary: (symbol, date) -> close_price
    stock_lookup = stock_hist.set_index(['symbol', 'date'])['close'].to_dict()
    
    # Create profile dictionary for O(1) lookups
    profile_lookup = mo_df.set_index('symbol').to_dict('index')
    
    processed_count = 0
    skipped_count = 0
    
    for idx, row in cw_hist.iterrows():
        symbol = row['symbol']
        cw_date = row['date']
        cw_price = row['close']
        cw_volume = row['volume']
        
        profile = profile_lookup.get(symbol)
        if not profile:
            skipped_count += 1
            continue
            
        underlying = profile['underlying']
        strike = profile['strike_price']
        ratio = profile['parsed_ratio']
        maturity_date = profile['maturity_date']
        
        # Days to maturity at that historical date
        days_to_mat = (maturity_date - cw_date).days
        if days_to_mat <= 2 or cw_price <= 0:
            skipped_count += 1
            continue # Skip expired/invalid
            
        # Get underlying price at that date
        s_price = stock_lookup.get((underlying, cw_date))
        if not s_price:
            skipped_count += 1
            continue
            
        # Get historical volatilities
        vol_df = underlying_vols.get(underlying)
        if vol_df is not None and cw_date in vol_df.index:
            hist_vol = vol_df.loc[cw_date, 'historical_volatility_pct']
            garch_vol = vol_df.loc[cw_date, 'garch_vol_forecast_pct']
        else:
            hist_vol = 45.0
            garch_vol = 45.0
            
        if pd.isna(hist_vol): hist_vol = 45.0
        if pd.isna(garch_vol): garch_vol = 45.0
            
        # Calculate Implied Volatility
        iv = estimate_implied_volatility(
            market_price=cw_price * ratio, # Normalize market price to 1 underlying share
            underlying_price=s_price,
            strike_price=strike,
            days_to_maturity=days_to_mat,
            risk_free_rate=RISK_FREE_RATE
        )
        iv_pct = iv * 100.0
        
        vol_for_pricing = garch_vol / 100.0
        
        # Calculate Greeks using GARCH vol (Prevents Target Leakage!)
        greeks = calculate_greeks_for_cw(
            underlying_price=s_price,
            strike_price=strike,
            days_to_maturity=days_to_mat,
            implied_volatility=vol_for_pricing,
            conversion_ratio=ratio,
            risk_free_rate=RISK_FREE_RATE
        )
        
        # Calculate BSM Theoretical Price using GARCH vol
        T = days_to_mat / 365.0
        d1_theo, d2_theo = calculate_d1_d2(s_price, strike, T, RISK_FREE_RATE, vol_for_pricing)
        bsm_theoretical_price_unscaled = s_price * norm.cdf(d1_theo) - strike * np.exp(-RISK_FREE_RATE * T) * norm.cdf(d2_theo)
        bsm_theoretical_price = bsm_theoretical_price_unscaled / ratio
        
        # Build record
        record = {
            'symbol': symbol,
            'date': cw_date.strftime('%Y-%m-%d'),
            'market_price': cw_price,
            'underlying_price': s_price,
            'strike_price': strike,
            'ratio': ratio,
            'days_to_maturity': days_to_mat,
            'volume': cw_volume,
            
            # Features
            'moneyness': greeks['moneyness'],
            'implied_volatility_pct': iv_pct,
            'historical_volatility_pct': hist_vol,
            'garch_vol_forecast_pct': garch_vol,
            
            'delta': greeks['delta'],
            'gamma': greeks['gamma'],
            'theta': greeks['theta'],
            'vega': greeks['vega'],
            'prob_itm': greeks['prob_itm'],
            
            # Theoretical BSM Benchmark
            'bsm_price': bsm_theoretical_price,
            'normalized_market_price': cw_price * ratio
        }
        backfill_data.append(record)
        processed_count += 1
        
        if processed_count % 5000 == 0:
            print(f"   ... processed {processed_count:,} rows")
            
    # 4. Save Dataset
    print(f"\n✅ Finished processing. Valid rows: {processed_count:,}. Skipped: {skipped_count:,}")
    
    out_dir = os.path.join("data", "processed")
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "ml_historical_dataset.csv")
    
    df_out = pd.DataFrame(backfill_data)
    df_out.to_csv(out_file, index=False)
    
    print("=" * 80)
    print(f"🎉 HYBRID ML DATASET GENERATED SUCCESSFULLY!")
    print(f"💾 Saved to: {out_file}")
    print("=" * 80)

if __name__ == '__main__':
    main()
