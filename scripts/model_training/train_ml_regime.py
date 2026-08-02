import sqlite3
import pandas as pd
import argparse
import sys
import warnings

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

from src.modules.regime_analysis.forecasting.dataset import RegimeDataset
from src.modules.regime_analysis.forecasting.xgboost_trainer import XGBoostRegimeTrainer

def main():
    parser = argparse.ArgumentParser(description="Train ML Forecaster for Market Regimes")
    parser.add_argument('--symbol', type=str, default='VNINDEX', help='Stock symbol to train on')
    parser.add_argument('--horizon', type=int, default=5, help='Prediction horizon (e.g., 5 days ahead)')
    args = parser.parse_args()

    print(f"🚀 Starting ML Training Pipeline for {args.symbol} (Horizon: T+{args.horizon})")
    
    # 1. Load Data
    try:
        conn = sqlite3.connect('data/finvista.db')
        query = f"SELECT date, open, high, low, close, volume FROM stock_history WHERE symbol = '{args.symbol}' ORDER BY date ASC"
        df = pd.read_sql(query, conn)
        conn.close()
        
        if df.empty:
            print(f"⚠️ No data found in database for {args.symbol}. Falling back to yfinance...")
            import yfinance as yf
            ticker = args.symbol
            if ticker == 'VNINDEX': ticker = '^VNINDEX'
            df = yf.download(ticker, start='2015-01-01', progress=False)
            df = df.reset_index()
            df = df.rename(columns={'Date': 'date', 'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'})
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            if df.empty:
                print(f"❌ Failed to fetch data for {args.symbol} from yfinance either.")
                sys.exit(1)
                
    except Exception as e:
        print(f"❌ Database error: {e}")
        sys.exit(1)

    df['date'] = pd.to_datetime(df['date'])
    
    # 2. Create Dataset
    print("\n⚙️ Generating Features and HMM Labels...")
    X, y = RegimeDataset.create_dataset(df, horizon=args.horizon)
    
    print(f"✅ Dataset ready: {len(X)} samples, {len(X.columns)} features.")
    
    # 3. Train Model
    trainer = XGBoostRegimeTrainer()
    trainer.train_and_evaluate(X, y, n_splits=5)
    
    # 4. Save Model
    model_name = f"xgboost_regime_{args.symbol}_T{args.horizon}.pkl"
    trainer.save_model(model_name)

if __name__ == "__main__":
    main()
