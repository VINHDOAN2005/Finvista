import pandas as pd
from typing import Tuple
from src.modules.regime_analysis.portfolio.regime_model import fit_vnindex_hmm
from src.modules.regime_analysis.forecasting.features import RegimeFeatureEngineer

class RegimeDataset:
    """
    Combines feature engineering with the historical HMM labels to create the final ML dataset.
    """
    
    @staticmethod
    def create_dataset(df_raw: pd.DataFrame, horizon: int = 5) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Creates X (features) and y (target regime at t+horizon).
        
        Args:
            df_raw: Raw OHLCV DataFrame
            horizon: Number of days ahead to predict
            
        Returns:
            X: Features DataFrame
            y: Target Series (0, 1, 2, 3)
        """
        df = df_raw.copy().sort_values('date' if 'date' in df_raw.columns else df_raw.index.name or 'index')
        
        # 1. Get True Historical Labels from the Hybrid Model
        # We fit the HMM on the entire historical dataset to get the "ground truth" regimes.
        from src.modules.regime_analysis.portfolio.regime_model import prepare_vnindex_features
        df = prepare_vnindex_features(df)
        hybrid_model, _ = fit_vnindex_hmm(df)
        states = hybrid_model.predict(df)
        
        # 2. Add labels to dataframe
        df['regime_label'] = states
        
        # 3. Create Target: Shift the label backwards by 'horizon'
        # Example: If today is Monday (T), the target Y is the regime on next Monday (T+5).
        df['target'] = df['regime_label'].shift(-horizon)
        
        # 4. Generate Features (X)
        features_df = RegimeFeatureEngineer.generate_features(df)
        
        # Merge target back
        # The features_df might have dropped rows due to NaN rolling windows
        dataset = features_df.join(df[['target']])
        
        # Drop the last 'horizon' rows because their target is NaN
        dataset = dataset.dropna(subset=['target'])
        
        X = dataset.drop(columns=['target'])
        y = dataset['target'].astype(int)
        
        return X, y
