import numpy as np
import pandas as pd
from src.modules.regime_analysis.portfolio.regime_model import calculate_kama

class RegimeFeatureEngineer:
    """
    Engineers features from stock/index price and volume data for Regime Forecasting.
    """
    
    @staticmethod
    def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss.replace(0, np.nan)
        return 100 - (100 / (1 + rs.fillna(0)))

    @staticmethod
    def calculate_macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple:
        fast_ema = series.ewm(span=fast, adjust=False).mean()
        slow_ema = series.ewm(span=slow, adjust=False).mean()
        macd = fast_ema - slow_ema
        macd_signal = macd.ewm(span=signal, adjust=False).mean()
        macd_hist = macd - macd_signal
        return macd, macd_signal, macd_hist

    @staticmethod
    def calculate_bollinger_bands(series: pd.Series, window: int = 20, num_std: float = 2.0) -> tuple:
        sma = series.rolling(window=window).mean()
        rolling_std = series.rolling(window=window).std()
        upper = sma + (rolling_std * num_std)
        lower = sma - (rolling_std * num_std)
        bb_width = (upper - lower) / sma
        return upper, lower, bb_width

    @staticmethod
    def generate_features(df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculates all ML features.
        Expects a DataFrame with 'close', 'high', 'low', 'volume' columns.
        """
        df = df.copy().sort_index()
        
        # 1. Trend & Momentum
        df['return_1d'] = df['close'].pct_change(1)
        df['return_5d'] = df['close'].pct_change(5)
        df['return_20d'] = df['close'].pct_change(20)
        
        df['rsi_14'] = RegimeFeatureEngineer.calculate_rsi(df['close'], 14)
        macd, macd_signal, macd_hist = RegimeFeatureEngineer.calculate_macd(df['close'])
        df['macd_hist'] = macd_hist
        
        df['kama_21'] = calculate_kama(df['close'], er_period=21, fast=5, slow=100)
        df['kama_slope'] = df['kama_21'].diff()
        
        df['sma_50'] = df['close'].rolling(50).mean()
        df['sma_200'] = df['close'].rolling(200).mean()
        df['dist_sma50'] = (df['close'] - df['sma_50']) / df['sma_50']
        df['dist_sma200'] = (df['close'] - df['sma_200']) / df['sma_200']
        
        # 2. Volatility
        df['volatility_10d'] = df['return_1d'].rolling(10).std() * np.sqrt(252)
        df['volatility_30d'] = df['return_1d'].rolling(30).std() * np.sqrt(252)
        
        _, _, bbw = RegimeFeatureEngineer.calculate_bollinger_bands(df['close'], 20)
        df['bb_width'] = bbw
        
        if 'high' in df.columns and 'low' in df.columns:
            df['true_range'] = df[['high', 'low', 'close']].apply(
                lambda row: max(row['high'] - row['low'], 
                                abs(row['high'] - row['close']), 
                                abs(row['low'] - row['close'])), axis=1
            )
            df['atr_14'] = df['true_range'].rolling(14).mean() / df['close']
        
        # 3. Volume
        df['vol_ma20'] = df['volume'].rolling(20).mean()
        df['log_volume_ratio'] = np.log(df['volume'] / df['vol_ma20'].replace(0, np.nan))
        
        # Clean up
        features = ['return_1d', 'return_5d', 'return_20d', 'rsi_14', 'macd_hist',
                    'kama_slope', 'dist_sma50', 'dist_sma200', 'volatility_10d', 
                    'volatility_30d', 'bb_width', 'log_volume_ratio']
                    
        if 'atr_14' in df.columns:
            features.append('atr_14')
            
        # Drop rows with NaN caused by rolling windows
        df = df.dropna(subset=features)
        
        return df[features]
