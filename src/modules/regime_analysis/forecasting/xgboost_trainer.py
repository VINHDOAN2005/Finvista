import os
import joblib
import pandas as pd
from typing import Tuple
from xgboost import XGBClassifier
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import classification_report, accuracy_score
from src.core import config

class XGBoostRegimeTrainer:
    """
    Trains an XGBoost model using TimeSeriesSplit to prevent look-ahead bias.
    """

    def __init__(self, model_dir: str = None):
        self.model_dir = model_dir or config.XGBOOST_REGIME_DIR
        if not os.path.exists(self.model_dir):
            os.makedirs(self.model_dir)
            
        self.model = XGBClassifier(
            objective='multi:softprob',
            num_class=4,
            eval_metric='mlogloss',
            learning_rate=0.05,
            max_depth=5,
            subsample=0.8,
            colsample_bytree=0.8,
            n_estimators=200,
            random_state=42
        )

    def train_and_evaluate(self, X: pd.DataFrame, y: pd.Series, n_splits: int = 5) -> XGBClassifier:
        """
        Evaluates the model using walk-forward validation and then trains on the full dataset.
        """
        print(f"🔄 Starting TimeSeries Walk-Forward Validation ({n_splits} splits)...")
        tscv = TimeSeriesSplit(n_splits=n_splits)
        
        fold = 1
        accuracies = []
        
        for train_index, test_index in tscv.split(X):
            X_train, X_test = X.iloc[train_index], X.iloc[test_index]
            y_train, y_test = y.iloc[train_index], y.iloc[test_index]
            
            # Use early stopping
            self.model.fit(
                X_train, y_train,
                eval_set=[(X_test, y_test)],
                verbose=False
            )
            
            y_pred = self.model.predict(X_test)
            acc = accuracy_score(y_test, y_pred)
            accuracies.append(acc)
            print(f"  Fold {fold}: Accuracy = {acc:.2%}")
            fold += 1
            
        print(f"✅ Mean CV Accuracy: {sum(accuracies)/len(accuracies):.2%}")
        
        print("\n🚀 Training final model on entire dataset...")
        self.model.fit(X, y)
        
        # Print final training report
        y_pred_full = self.model.predict(X)
        print("\n📊 Final Model Training Report:")
        print(classification_report(y, y_pred_full, target_names=["Bullish Low Vol", "Bullish High Vol", "Bearish Low Vol", "Bearish High Vol"], zero_division=0))
        
        return self.model

    def save_model(self, filename: str = "xgboost_regime_model.pkl"):
        path = os.path.join(self.model_dir, filename)
        joblib.dump(self.model, path)
        print(f"💾 Model saved to {path}")

    def load_model(self, filename: str = "xgboost_regime_model.pkl"):
        path = os.path.join(self.model_dir, filename)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Model not found at {path}")
        self.model = joblib.load(path)
        print(f"📂 Model loaded from {path}")
        return self.model
