import sqlite3
import pandas as pd
import argparse
import sys
import warnings

warnings.filterwarnings('ignore')

from src.modules.regime_analysis.forecasting.features import RegimeFeatureEngineer
from src.modules.regime_analysis.forecasting.xgboost_trainer import XGBoostRegimeTrainer

LABEL_MAP = {
    0: "Bullish (Low Volatility)",
    1: "Bullish (High Volatility)",
    2: "Bearish (Low Volatility)",
    3: "Bearish Crisis (High Volatility)"
}

def main():
    parser = argparse.ArgumentParser(description="Predict Future Market Regime")
    parser.add_argument('--symbol', type=str, default='VNINDEX', help='Stock symbol to predict for')
    parser.add_argument('--horizon', type=int, default=5, help='Prediction horizon (T+N)')
    args = parser.parse_args()

    print(f"🔮 ML Regime Predictor for {args.symbol} (Horizon: T+{args.horizon})")
    
    # 1. Load Model
    model_name = f"xgboost_regime_VNINDEX_T{args.horizon}.pkl" # Always use VNINDEX model as macro base if wanted, but let's use symbol specific
    model_name = f"xgboost_regime_{args.symbol}_T{args.horizon}.pkl"
    
    trainer = XGBoostRegimeTrainer()
    try:
        model = trainer.load_model(model_name)
    except FileNotFoundError:
        print(f"❌ Model {model_name} not found. Please run train_ml_regime.py first.")
        sys.exit(1)

    # 2. Load Data
    try:
        conn = sqlite3.connect('data/finvista.db')
        # We need enough data to calculate all features (e.g., SMA-200 needs 200 rows)
        query = f"SELECT date, open, high, low, close, volume FROM stock_history WHERE symbol = '{args.symbol}' ORDER BY date DESC LIMIT 300"
        df = pd.read_sql(query, conn)
        conn.close()
        
        if df.empty:
            import yfinance as yf
            ticker = args.symbol
            if ticker == 'VNINDEX': ticker = '^VNINDEX'
            df = yf.download(ticker, period='2y', progress=False)
            df = df.reset_index()
            df = df.rename(columns={'Date': 'date', 'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'})
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            if df.empty:
                print(f"❌ No data found for {args.symbol}.")
                sys.exit(1)
            
        df = df.sort_values('date').reset_index(drop=True)
        df['date'] = pd.to_datetime(df['date'])
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        sys.exit(1)

    # 3. Generate Features for the latest day
    features_df = RegimeFeatureEngineer.generate_features(df)
    
    if features_df.empty:
        print("❌ Not enough data to generate features.")
        sys.exit(1)
        
    latest_features = features_df.iloc[[-1]]
    latest_date = df['date'].iloc[-1].strftime('%Y-%m-%d')
    
    # 4. Predict
    probabilities = model.predict_proba(latest_features)[0]
    predicted_class = model.predict(latest_features)[0]
    
    print("\n" + "="*60)
    print(f"📅 Current Date: {latest_date}")
    print(f"🎯 Target Prediction Date: T+{args.horizon} days")
    print("="*60)
    print("\n📊 REGIME PROBABILITIES:")
    
    for i, prob in enumerate(probabilities):
        star = "⭐⭐⭐" if i == predicted_class else "   "
        print(f"  {star} {LABEL_MAP[i]:<35}: {prob:.1%}")
        
    print("\n" + "="*60)
    print(f"🔥 FINAL VERDICT: {LABEL_MAP[predicted_class]}")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
