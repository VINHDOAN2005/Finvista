# -*- coding: utf-8 -*-
"""
🤖 ML PRICING MODEL - TRAIN, TEST, SIMULATE
============================================
Train ML model on historical CW data, test performance, and simulate trading.

Based on research showing ML can outperform traditional option pricing models.
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import warnings
warnings.filterwarnings('ignore')

from src.modules.cw_pricing.models.pricing_core import RISK_FREE_RATE

print("=" * 80)
print("ML T+5 VOLATILITY FORECASTER & HYBRID PRICING")
print("=" * 80)

# ==========================================
# 1. LOAD DATA
# ==========================================

print("\n" + "=" * 80)
print("1. LOAD HISTORICAL DATA")
print("=" * 80)

import os

dataset_path = os.path.join("data", "processed", "ml_historical_dataset.csv")
if os.path.exists(dataset_path):
    print(f"📥 Loading massive historical dataset from {dataset_path}...")
    df = pd.read_csv(dataset_path)
else:
    print(f"❌ Error: Dataset not found. Please run backfill_ml_data.py first.")
    exit(1)
    
# Filter valid data
df = df.dropna(subset=[
    'market_price', 'underlying_price', 'strike_price', 
    'days_to_maturity', 'implied_volatility_pct'
])
df['normalized_price'] = df['normalized_market_price']

# Sort chronologically to prevent Look-ahead Bias
if 'date' in df.columns:
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(['symbol', 'date']).reset_index(drop=True)
    print("🕒 Data sorted chronologically by symbol.")

print(f"📊 Valid samples after filtering: {len(df)}")

# ==========================================
# 2. CREATE T+5 TARGET (THE SECRET SAUCE)
# ==========================================
# Instead of predicting today's price, we predict the Implied Volatility 5 days from now.

# Convert IV pct to decimal
df['iv_decimal'] = df['implied_volatility_pct'] / 100.0

# Create T+5 target using groupby and shift (-5 means 5 rows into the future)
df['target_iv_t5'] = df.groupby('symbol')['iv_decimal'].shift(-5)

# We also want to know the actual underlying price at T+5 to evaluate our trading simulation later
df['actual_S_t5'] = df.groupby('symbol')['underlying_price'].shift(-5)
df['actual_market_price_t5'] = df.groupby('symbol')['normalized_price'].shift(-5)

# Drop rows where we don't have T+5 data (the last 5 days of each symbol's history)
df_clean = df.dropna(subset=['target_iv_t5', 'actual_market_price_t5']).copy()

print(f"📊 Samples with T+5 Target available: {len(df_clean)}")

# ==========================================
# 3. PREPARE FEATURES
# ==========================================

print("\n" + "=" * 80)
print("2. PREPARE FEATURES FOR ML MODEL")
print("=" * 80)

def create_features(df):
    """Create features for ML pricing model based on research."""
    features = pd.DataFrame(index=df.index)
    
    # Basic pricing inputs
    features['S'] = df['underlying_price']
    features['K'] = df['strike_price']
    features['T'] = df['days_to_maturity'] / 365.0
    
    # Moneyness features
    features['moneyness'] = df['underlying_price'] / df['strike_price']
    features['log_moneyness'] = np.log(features['moneyness'])
    
    # Volatility features
    features['historical_volatility'] = df.get('historical_volatility_pct', 45.0) / 100.0
    features['garch_vol_forecast'] = df.get('garch_vol_forecast_pct', features['historical_volatility']) / 100.0
    
    # The current IV is a strong baseline predictor for future IV
    features['current_iv'] = df['iv_decimal']
    
    # IV spread (Is the current IV higher or lower than GARCH forecast?)
    features['iv_garch_spread'] = features['current_iv'] - features['garch_vol_forecast']
    
    # Liquidity features
    features['volume'] = df.get('volume', 0)
    
    # Greeks (useful features)
    features['delta'] = df['delta']
    features['gamma'] = df['gamma']
    features['theta'] = df['theta']
    features['vega'] = df['vega']
    
    # Probability features
    features['prob_itm'] = df['prob_itm']
    
    # Fill NaN with 0 for models
    features = features.fillna(0)
    
    return features

X = create_features(df_clean)
y = df_clean['target_iv_t5']  # Target: T+5 Implied Volatility

print(f"📊 Features shape: {X.shape}")
print(f"📊 Target shape: {y.shape}")

# ==========================================
# 4. SPLIT TRAIN/TEST
# ==========================================

print("\n" + "=" * 80)
print("3. SPLIT TRAIN/TEST SETS")
print("=" * 80)

# Use 80% train, 20% test. CRITICAL: shuffle=False to prevent look-ahead bias!
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, shuffle=False
)

print(f"📊 Train set: {len(X_train)} samples")
print(f"📊 Test set: {len(X_test)} samples")

# ==========================================
# 5. TRAIN ML MODEL
# ==========================================

print("\n" + "=" * 80)
print("4. TRAIN XGBOOST MODEL (T+5 VOLATILITY)")
print("=" * 80)

model = xgb.XGBRegressor(
    n_estimators=300,
    learning_rate=0.05,
    max_depth=4,               
    min_child_weight=3,        
    subsample=0.8,
    colsample_bytree=0.8,
    reg_alpha=0.1,             
    reg_lambda=1.0,            
    random_state=42,
    n_jobs=-1
)

print("🔄 Training model...")
model.fit(X_train, y_train, verbose=False)
print("✅ Training completed!")

# Feature importance
feature_importance = pd.DataFrame({
    'feature': X.columns,
    'importance': model.feature_importances_
}).sort_values('importance', ascending=False)

print("\n📊 Top 10 Important Features (Predicting IV):")
print(feature_importance.head(10).to_string(index=False))

# ==========================================
# 6. TEST MODEL PERFORMANCE (VOLATILITY)
# ==========================================

print("\n" + "=" * 80)
print("5. VOLATILITY PREDICTION PERFORMANCE")
print("=" * 80)

y_test_pred = model.predict(X_test)

test_mae = mean_absolute_error(y_test, y_test_pred)
test_rmse = np.sqrt(mean_squared_error(y_test, y_test_pred))
test_r2 = r2_score(y_test, y_test_pred)

print(f"📈 TEST SET (IV Prediction):")
print(f"   MAE: {test_mae:.4f} ({test_mae*100:.2f}%)")
print(f"   RMSE: {test_rmse:.4f}")
print(f"   R²: {test_r2:.4f}")

# Baseline (Predicting that T+5 IV will just be the same as Today's IV)
baseline_mae = mean_absolute_error(y_test, X_test['current_iv'])
print(f"\n📈 BASELINE (Today's IV = T+5 IV):")
print(f"   MAE: {baseline_mae:.4f} ({baseline_mae*100:.2f}%)")

if test_mae < baseline_mae:
    print(f"🏆 ML Model beats Baseline by {(baseline_mae - test_mae)/baseline_mae*100:.2f}%")
else:
    print(f"⚠️ ML Model is worse than Baseline.")

# ==========================================
# 7. HYBRID PRICING & SIMULATION
# ==========================================

print("\n" + "=" * 80)
print("6. HYBRID BSM PRICING & TRADING SIMULATION")
print("=" * 80)

from src.modules.cw_pricing.models.pricing_core import calculate_d1_d2
from scipy.stats import norm

test_df = df_clean.loc[X_test.index].copy()
test_df['predicted_iv_t5'] = y_test_pred

# Calculate the Expected Future Price at T+5 using Black-Scholes
expected_prices_t5 = []
for idx in test_df.index:
    row = test_df.loc[idx]
    # We assume the underlying price S doesn't change wildly, or we use a slight drift. 
    # For this simulation, we'll test if predicting IV alone is enough.
    # A true hedge fund would also predict S_t5, but S is a random walk. 
    # Let's assume S stays constant, but time decays by 5 days, and Volatility goes to predicted_iv_t5.
    
    S = row['underlying_price']
    K = row['strike_price']
    T_future = max((row['days_to_maturity'] - 5) / 365.0, 0.001) # 5 days later
    r = RISK_FREE_RATE
    sigma_future = max(row['predicted_iv_t5'], 0.01)
    
    if T_future > 0 and S > 0 and K > 0:
        d1, d2 = calculate_d1_d2(S, K, T_future, r, sigma_future)
        expected_price_t5 = S * norm.cdf(d1) - K * np.exp(-r * T_future) * norm.cdf(d2)
        expected_prices_t5.append(expected_price_t5)
    else:
        expected_prices_t5.append(row['intrinsic_value'])

test_df['expected_price_t5'] = expected_prices_t5
test_df['current_market_price'] = test_df['normalized_price']

# Calculate expected upside based on our Hybrid Model
test_df['hybrid_upside_pct'] = (test_df['expected_price_t5'] - test_df['current_market_price']) / test_df['current_market_price'] * 100

# Generate Trading Signals
# Buy if the hybrid model expects the price to be > 10% higher in 5 days
test_df['hybrid_signal'] = np.where(test_df['hybrid_upside_pct'] > 10, 'BUY', 
                                np.where(test_df['hybrid_upside_pct'] < -10, 'SELL', 'HOLD'))

print(f"📊 Hybrid Model Signals:")
print(test_df['hybrid_signal'].value_counts())

# Evaluate Actual Trading Performance
# We bought at 'current_market_price'. 5 days later, the actual price is 'actual_market_price_t5'
test_df['actual_profit_pct'] = (test_df['actual_market_price_t5'] - test_df['current_market_price']) / test_df['current_market_price'] * 100

buy_trades = test_df[test_df['hybrid_signal'] == 'BUY']
if len(buy_trades) > 0:
    win_rate = (buy_trades['actual_profit_pct'] > 0).mean() * 100
    avg_profit = buy_trades['actual_profit_pct'].mean()
    print(f"\n💰 TRADING PERFORMANCE (T+5 HOLDING PERIOD):")
    print(f"   Total BUY trades executed: {len(buy_trades)}")
    print(f"   Win Rate: {win_rate:.2f}%")
    print(f"   Average Profit per Trade: {avg_profit:.2f}%")
else:
    print("No BUY signals generated.")

print("\n" + "=" * 80)
print("7. SAVE MODEL")
print("=" * 80)

import joblib

model_dir = 'artifacts'
if not os.path.exists(model_dir):
    os.makedirs(model_dir)

model_path = os.path.join(model_dir, 'ml_hybrid_vol_model.pkl')
joblib.dump(model, model_path)

print(f"✅ Hybrid Volatility Model saved to: {model_path}")
print("================================================================================")
