# -*- coding: utf-8 -*-
"""
📊 NEWS STEP 6: MACHINE LEARNING CLASSIFIER TRAINING
===================================================
Engineers features (AI sentiment, historical stock momentum, volatility, market volatility),
aligns them with forward 5-day CAR target labels, splits train/test sets chronologically,
and trains a Random Forest Classifier to predict outperformance.
"""

import os
import numpy as np
import pandas as pd
from src.core.utils import logger

try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import classification_report, accuracy_score, roc_auc_score, confusion_matrix
    import joblib
    sklearn_available = True
except ImportError:
    sklearn_available = False

MODEL_PATH = os.path.join("data", "processed", "news_ml_model.joblib")

def train_news_ml_model(
    df_returns: pd.DataFrame, 
    prices_map: dict, 
    market_returns: dict,
    horizon_target: int = 5
) -> dict:
    """
    Build features, perform grid search over Random Forest, Gradient Boosting, and XGBoost,
    train the best model, and evaluate metrics.
    """
    logger.info(f"🎬 [Step 6] Initializing Machine Learning Model Training (Target: CAR {horizon_target}d > 0)...")
    
    if not sklearn_available:
        logger.error("❌ scikit-learn or joblib is not installed. Cannot train ML model.")
        return {}
        
    target_col = f"car_{horizon_target}d"
    if target_col not in df_returns.columns:
        logger.error(f"❌ Target column '{target_col}' not found in returns DataFrame.")
        return {}
        
    dataset_rows = []
    
    for _, row in df_returns.iterrows():
        sym = row["symbol"]
        if sym not in prices_map:
            continue
            
        df_prices = prices_map[sym]
        news_date = row["news_date"]
        aligned_date = row["aligned_date"]
        
        # Find index of aligned_date
        match_idx = df_prices[df_prices["date"] == aligned_date].index
        if match_idx.empty:
            continue
        idx_0 = match_idx[0]
        
        # We need at least 30 sessions of history prior to news for volatility calculation
        if idx_0 < 30:
            continue
            
        # 1. Feature Engineering
        # a. Sentiment (One-hot encoded manually)
        sent = row["sentiment"]
        is_pos = 1.0 if sent == "POSITIVE" else 0.0
        is_neg = 1.0 if sent == "NEGATIVE" else 0.0
        is_neu = 1.0 if sent == "NEUTRAL" else 0.0
        
        # b. Stock daily returns & closes
        closes = df_prices["close"].values
        daily_returns = df_prices["close"].pct_change().values
        volumes = df_prices["volume"].values
        
        # c. Stock historical volatility (10d, 20d, 30d std of daily returns prior to news)
        vol_10d = np.std(daily_returns[idx_0 - 10 : idx_0])
        vol_20d = np.std(daily_returns[idx_0 - 20 : idx_0])
        vol_30d = np.std(daily_returns[idx_0 - 30 : idx_0])
        
        # d. Stock momentum (1d, 5d, 10d, 20d returns prior to news)
        ref_1d = closes[idx_0 - 2] if idx_0 >= 2 else closes[0]
        momentum_1d = (closes[idx_0 - 1] - ref_1d) / ref_1d if ref_1d > 0 else 0.0
        
        ref_5d = closes[idx_0 - 6] if idx_0 >= 6 else closes[0]
        momentum_5d = (closes[idx_0 - 1] - ref_5d) / ref_5d if ref_5d > 0 else 0.0
        
        ref_10d = closes[idx_0 - 11] if idx_0 >= 11 else closes[0]
        momentum_10d = (closes[idx_0 - 1] - ref_10d) / ref_10d if ref_10d > 0 else 0.0
        
        ref_20d = closes[idx_0 - 21] if idx_0 >= 21 else closes[0]
        momentum_20d = (closes[idx_0 - 1] - ref_20d) / ref_20d if ref_20d > 0 else 0.0
        
        # e. Stock volume ratios
        vol_avg_30d = np.mean(volumes[idx_0 - 30 : idx_0])
        volume_ratio_1d = volumes[idx_0 - 1] / vol_avg_30d if vol_avg_30d > 0 else 1.0
        volume_ratio_5d = np.mean(volumes[idx_0 - 5 : idx_0]) / vol_avg_30d if vol_avg_30d > 0 else 1.0
        
        # f. Market historical volatility & momentum prior to news
        market_vols = []
        for offset in range(-30, 0):
            curr_date = df_prices.iloc[idx_0 + offset]["date"]
            market_vols.append(market_returns.get(curr_date, 0.0))
            
        market_vol_30d = np.std(market_vols) if market_vols else 0.0
        
        # Market momentum (5d)
        market_vols_5d = market_vols[-5:] if len(market_vols) >= 5 else market_vols
        market_momentum_5d = np.prod([1.0 + r for r in market_vols_5d]) - 1.0 if market_vols_5d else 0.0
        
        # g. Target label: 1 if CAR > 0 else 0
        car_val = row[target_col]
        if np.isnan(car_val):
            continue
        target_label = 1 if car_val > 0.0 else 0
        
        dataset_rows.append({
            "news_date": news_date,
            "is_positive": is_pos,
            "is_negative": is_neg,
            "is_neutral": is_neu,
            "stock_vol_10d": vol_10d,
            "stock_vol_20d": vol_20d,
            "stock_vol_30d": vol_30d,
            "stock_momentum_1d": momentum_1d,
            "stock_momentum_5d": momentum_5d,
            "stock_momentum_10d": momentum_10d,
            "stock_momentum_20d": momentum_20d,
            "stock_volume_ratio_1d": volume_ratio_1d,
            "stock_volume_ratio_5d": volume_ratio_5d,
            "market_vol_30d": market_vol_30d,
            "market_momentum_5d": market_momentum_5d,
            "target": target_label
        })
        
    df_ml = pd.DataFrame(dataset_rows)
    if len(df_ml) < 10:
        logger.warning(f"⚠️ Insufficient samples for ML training. Need at least 10, found {len(df_ml)}")
        return {}
        
    # Sort chronologically to prevent look-ahead bias
    df_ml = df_ml.sort_values("news_date").reset_index(drop=True)
    
    # Feature matrix X and target y
    feature_cols = [
        "is_positive", "is_negative", "is_neutral", 
        "stock_vol_10d", "stock_vol_20d", "stock_vol_30d",
        "stock_momentum_1d", "stock_momentum_5d", "stock_momentum_10d", "stock_momentum_20d",
        "stock_volume_ratio_1d", "stock_volume_ratio_5d",
        "market_vol_30d", "market_momentum_5d"
    ]
    X = df_ml[feature_cols]
    y = df_ml["target"]
    
    # Time-series split: 80% train, 20% test
    split_idx = int(len(df_ml) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
    
    logger.info(f"📊 Dataset split: Train={len(X_train)} samples, Test={len(X_test)} samples.")
    
    # Check class balance
    train_pos_pct = np.mean(y_train) * 100
    test_pos_pct = np.mean(y_test) * 100
    logger.info(f"⚖️ Target class balance (positive rate): Train={train_pos_pct:.1f}%, Test={test_pos_pct:.1f}%")
    
    # Hyperparameter Grid Search with TimeSeriesSplit
    from sklearn.model_selection import GridSearchCV, TimeSeriesSplit
    from sklearn.ensemble import GradientBoostingClassifier
    
    cv = TimeSeriesSplit(n_splits=3)
    
    models_to_test = {}
    
    # Random Forest Grid
    models_to_test["Random Forest"] = (
        RandomForestClassifier(random_state=42),
        {
            "n_estimators": [50, 100, 150],
            "max_depth": [3, 4, 5],
            "min_samples_split": [2, 5],
            "class_weight": ["balanced", None]
        }
    )
    
    # Gradient Boosting Grid
    models_to_test["Gradient Boosting"] = (
        GradientBoostingClassifier(random_state=42),
        {
            "n_estimators": [50, 100],
            "max_depth": [3, 4],
            "learning_rate": [0.01, 0.05, 0.1]
        }
    )
    
    # XGBoost Grid if available
    try:
        from xgboost import XGBClassifier
        models_to_test["XGBoost"] = (
            XGBClassifier(random_state=42, eval_metric="logloss"),
            {
                "n_estimators": [50, 100],
                "max_depth": [3, 4],
                "learning_rate": [0.01, 0.05, 0.1]
            }
        )
    except ImportError:
        pass
        
    best_model_name = None
    best_score = -1.0
    best_estimator = None
    
    for name, (clf, param_grid) in models_to_test.items():
        logger.info(f"⚙️ Running Grid Search for {name}...")
        grid = GridSearchCV(clf, param_grid, cv=cv, scoring="roc_auc", n_jobs=-1)
        try:
            grid.fit(X_train, y_train)
            val_score = grid.best_score_
            logger.info(f"   🏆 Best CV ROC-AUC: {val_score:.4f} with params: {grid.best_params_}")
            if val_score > best_score:
                best_score = val_score
                best_model_name = name
                best_estimator = grid.best_estimator_
        except Exception as e:
            logger.warning(f"⚠️ Grid search failed for {name}: {e}")
            
    # Fallback to default Random Forest if all grid searches failed
    if best_estimator is None:
        logger.warning("⚠️ All grid searches failed. Falling back to default Random Forest.")
        best_model_name = "Random Forest (Fallback)"
        best_estimator = RandomForestClassifier(n_estimators=100, max_depth=3, random_state=42)
        best_estimator.fit(X_train, y_train)
        
    logger.info(f"👑 Selected Best Model: {best_model_name} (Train CV ROC-AUC: {best_score:.4f})")
    
    # Train final model on all training data
    model = best_estimator
    model.fit(X_train, y_train)
    
    # Predict on test set
    y_pred = model.predict(X_test)
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    
    # Calculate performance metrics
    acc = accuracy_score(y_test, y_pred)
    
    try:
        auc = roc_auc_score(y_test, y_pred_proba)
    except Exception:
        auc = 0.5 # fallback if only one class is present in y_test
        
    # Print ML Report
    print("\n" + "="*80)
    print("🤖  BÁO CÁO HUẤN LUYỆN MÔ HÌNH HỌC MÁY (TỐI ƯU HÓA HÌNH THỨC)  🤖")
    print("="*80)
    print(f" * Mô hình tốt nhất được chọn:  {best_model_name}")
    print(f" * Tổng số mẫu dữ liệu sạch:    {len(df_ml)}")
    print(f" * Số mẫu huấn luyện (Train):   {len(X_train)}")
    print(f" * Số mẫu kiểm thử (Test):     {len(X_test)}")
    print("-"*80)
    print(f" 🎯 Độ chính xác mô hình (Accuracy): {acc * 100:.2f}%")
    print(f" 📈 Chỉ số ROC-AUC:                  {auc:.4f}")
    print("-"*80)
    
    print(" 📋 Báo cáo phân loại chi tiết (Classification Report):")
    print(classification_report(y_test, y_pred, zero_division=0))
    
    # Feature Importances (only for models that support it)
    if hasattr(model, "feature_importances_"):
        importances = model.feature_importances_
        print(" 🛠️  Mức độ quan trọng của đặc trưng (Feature Importances):")
        for col, imp in sorted(zip(feature_cols, importances), key=lambda x: x[1], reverse=True):
            print(f"   - {col:<25} : {imp * 100:>6.2f}%")
            
    # Save the trained model
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    logger.info(f"💾 Model successfully saved to {MODEL_PATH}")
    print("="*80 + "\n")
    
    return {
        "model_name": best_model_name,
        "accuracy": acc,
        "roc_auc": auc,
        "feature_importances": dict(zip(feature_cols, model.feature_importances_)) if hasattr(model, "feature_importances_") else {}
    }
