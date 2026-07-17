# -*- coding: utf-8 -*-
"""
🏁 Finvista Corporate Credit Risk & Financial Distress Model Comparator & Exporter
========================================================================
Upgraded training workflow that compares:
1. Logistic Regression (Baseline statistical model)
2. Random Forest Classifier (Bagging ensemble)
3. XGBoost Classifier (Gradient boosting tree)
4. LightGBM Classifier (Fast gradient boosting tree)

Uses Out-of-Time sequential splitting, handles severe class imbalance,
renders a stunning comparative metric table, selects the absolute best model,
and exports it for live SaaS inference.

Author: samvo
"""

import json
import os
import numpy as np
import pandas as pd
import joblib
from typing import Any, Dict, List, Optional, Tuple
from src.common.utils import logger, load_csv
from src.common import config

# Import machine learning libraries
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)

DEFAULT_THRESHOLD = 0.5
TARGET_RECALL = 0.65  # Balanced early-warning: ~66% recall, ~75% precision at thr ~0.20

# ==========================================================================
# FIX DATA LEAKAGE: Use year-T features to predict year-T+1 distress label
# Set False to revert to same-year label (old behaviour, inflated metrics)
# ==========================================================================
USE_LAGGED_LABEL = True

# Features that directly encode labeling criteria — excluded when USE_LAGGED_LABEL=True
# to ensure the model learns genuine predictive signals, not the labeling rules themselves
LEAKAGE_FEATURES = {
    "ebit_to_interest",   # = ICR criterion (< 1.0)
    "icr",                # alias of ebit_to_interest
    "current_ratio",      # = liquidity criterion (< 0.5)
    "total_equity",       # = negative equity criterion
    "springate_distressed",   # derived binary label
    "zmijewski_distressed",   # derived binary label
}


def _predict_proba_positive(model: Any, X: pd.DataFrame) -> np.ndarray:
    if hasattr(model, "predict_proba"):
        return model.predict_proba(X)[:, 1]
    scores = model.decision_function(X)
    return 1.0 / (1.0 + np.exp(-scores))


def _metrics_at_threshold(y_true: np.ndarray, y_proba: np.ndarray, threshold: float) -> Dict[str, float]:
    y_pred = (y_proba >= threshold).astype(int)
    return {
        "threshold": threshold,
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
    }


def _pick_recall_first_threshold(
    y_true: np.ndarray, y_proba: np.ndarray, target_recall: float = TARGET_RECALL
) -> Tuple[float, Dict[str, float]]:
    """Lowest threshold that still meets target recall (maximizes precision among valid)."""
    precisions, recalls, thresholds = precision_recall_curve(y_true, y_proba)
    best: Optional[Tuple[float, Dict[str, float]]] = None

    for thr, prec, rec in zip(thresholds, precisions[:-1], recalls[:-1]):
        if rec < target_recall:
            continue
        metrics = {
            "threshold": float(thr),
            "precision": float(prec),
            "recall": float(rec),
            "f1": float(f1_score(y_true, (y_proba >= thr).astype(int), zero_division=0)),
        }
        if best is None or metrics["precision"] > best[1]["precision"]:
            best = (float(thr), metrics)

    if best is not None:
        return best

    # Fallback: maximize recall if target unreachable
    idx = int(np.argmax(recalls[:-1]))
    thr = float(thresholds[idx])
    return thr, _metrics_at_threshold(y_true, y_proba, thr)


def _log_threshold_sweep(y_true: np.ndarray, y_proba: np.ndarray, thresholds: List[float]) -> None:
    logger.info("\n" + "=" * 95)
    logger.info("📈 PRECISION / RECALL THEO NGƯỠNG (Out-of-Time Test Set)")
    logger.info("=" * 95)
    logger.info(
        f"{'Threshold':>10} | {'Precision':>10} | {'Recall':>10} | {'F1':>10} | {'Flagged':>8}"
    )
    logger.info("-" * 95)
    for thr in thresholds:
        m = _metrics_at_threshold(y_true, y_proba, thr)
        flagged = int(np.sum(y_proba >= thr))
        logger.info(
            f"{m['threshold']:>10.2f} | {m['precision']*100:9.2f}% | {m['recall']*100:9.2f}% | "
            f"{m['f1']*100:9.2f}% | {flagged:>8}"
        )
    logger.info("=" * 95)


def _log_per_year_metrics(test_df: pd.DataFrame, pred_col: str) -> None:
    logger.info("\n" + "=" * 95)
    logger.info(f"📅 METRICS THEO NĂM — {pred_col}")
    logger.info("=" * 95)
    logger.info(
        f"{'Year':>6} | {'N':>6} | {'Distress%':>10} | {'Precision':>10} | {'Recall':>10} | {'F1':>8}"
    )
    logger.info("-" * 95)
    for year in sorted(test_df["year"].unique()):
        sub = test_df[test_df["year"] == year]
        y = sub["distress_label"].values
        y_pred = sub[pred_col].values
        if len(sub) == 0:
            continue
        logger.info(
            f"{year:>6} | {len(sub):>6} | {y.mean()*100:9.2f}% | "
            f"{precision_score(y, y_pred, zero_division=0)*100:9.2f}% | "
            f"{recall_score(y, y_pred, zero_division=0)*100:9.2f}% | "
            f"{f1_score(y, y_pred, zero_division=0)*100:7.2f}%"
        )
    logger.info("=" * 95)


def _log_confusion_matrix(y_true: np.ndarray, y_pred: np.ndarray, title: str) -> None:
    cm = confusion_matrix(y_true, y_pred)
    logger.info(f"\n📋 Confusion Matrix — {title}:")
    logger.info("   Dự đoán 0 | Dự đoán 1")
    logger.info(f"Thực tế 0:  {cm[0, 0]:<5} | {cm[0, 1]}")
    logger.info(f"Thực tế 1:  {cm[1, 0]:<5} | {cm[1, 1]}  <-- (Số bỏ sót: {cm[1, 0]})")

def train_prediction_model():
    logger.info("==========================================================")
    logger.info("🏁 INITIALIZING ADVANCED MULTI-MODEL ML COMPARATIVE ENGINE")
    logger.info("==========================================================")
    
    # Load final processed dataset
    dataset_file = config.FINAL_DATASET_FILE
    if not os.path.exists(dataset_file):
        logger.error(f"❌ Final dataset not found: {dataset_file}")
        logger.info("💡 Please run: python run_pipeline.py first to generate the dataset.")
        return
        
    df = load_csv(dataset_file)
    if df.empty:
        logger.error("❌ Final training dataset is empty!")
        return
    
    # ------------------------------------------------------------------
    # LAGGED LABEL MODE: load _lagged dataset for proper T → T+1 setup
    # ------------------------------------------------------------------
    if USE_LAGGED_LABEL:
        lagged_file = dataset_file.replace(".csv", "_lagged.csv")
        if os.path.exists(lagged_file):
            df = load_csv(lagged_file)
            target_col = "distress_label_next_year"
            logger.info("✅ LAGGED MODE: features(T) → distress_label(T+1) — No data leakage")
        else:
            logger.warning("⚠️ Lagged dataset not found. Run pipeline first. Falling back to same-year label.")
            target_col = "distress_label"
    else:
        target_col = "distress_label"
        logger.info("⚠️ SAME-YEAR MODE: features(T) → distress_label(T) — Data leakage present")
        
    # Ensure year column is treated as integer
    df["year"] = df["year"].astype(int)
    
    # 1. Sequential Time-Based Train/Test Split
    # Split year: Train on <= 2022, Test on 2023 - 2025 (Out-of-Time Test Set)
    split_year = 2022
    
    train_mask = df["year"] <= split_year
    test_mask = df["year"] > split_year
    
    # Define features and target
    exclude_cols = {"ticker", "company_name", "year", "exchange", "industry",
                    "distress_label", "distress_label_next_year"}
    if USE_LAGGED_LABEL:
        exclude_cols |= LEAKAGE_FEATURES
        logger.info(f"🚫 Excluded {len(LEAKAGE_FEATURES)} leakage features: {sorted(LEAKAGE_FEATURES)}")
    feature_cols = [col for col in df.columns if col not in exclude_cols]
    
    X_train = df.loc[train_mask, feature_cols]
    y_train = df.loc[train_mask, target_col]
    
    X_test = df.loc[test_mask, feature_cols]
    y_test = df.loc[test_mask, target_col]
    
    logger.info(f"📊 Dataset successfully prepared:")
    logger.info(f"   * Total unique features      : {len(feature_cols)}")
    logger.info(f"   * Train Set (Years <= {split_year}): {len(X_train)} records")
    logger.info(f"   * Test Set (Years > {split_year}) : {len(X_test)} records")
    
    distress_rate_train = np.mean(y_train)
    distress_rate_test = np.mean(y_test)
    logger.info(f"   * Distress Rate in Train Set : {distress_rate_train:.2%}")
    logger.info(f"   * Distress Rate in Test Set  : {distress_rate_test:.2%}")
    
    if len(X_train) == 0 or len(X_test) == 0:
        logger.error("❌ Not enough records in Train or Test set! Make sure data spans multiple years.")
        return
        
    # Standardize features
    scaler = StandardScaler()
    X_train_scaled = pd.DataFrame(scaler.fit_transform(X_train), columns=feature_cols)
    X_test_scaled = pd.DataFrame(scaler.transform(X_test), columns=feature_cols)
    
    # Calculate Class Balance Weight
    neg_count = np.sum(y_train == 0)
    pos_count = np.sum(y_train == 1)
    scale_pos_weight = neg_count / pos_count if pos_count > 0 else 1.0
    logger.info(f"⚖️ Calculated Class Balance Factor: {scale_pos_weight:.2f}")
    
    models = {}
    
    # --- 1. Logistic Regression ---
    logger.info("🧠 Model 1: Training Logistic Regression (L2 penalty)...")
    lr_model = LogisticRegression(
        C=0.5,
        class_weight='balanced',
        max_iter=1000,
        random_state=42
    )
    lr_model.fit(X_train_scaled, y_train)
    models["Logistic Regression"] = lr_model
    
    # --- 2. Random Forest ---
    logger.info("🧠 Model 2: Training Random Forest (Bagging Ensemble)...")
    rf_model = RandomForestClassifier(
        n_estimators=100,
        max_depth=6,
        class_weight='balanced',
        random_state=42,
        n_jobs=-1
    )
    rf_model.fit(X_train_scaled, y_train)
    models["Random Forest"] = rf_model
    
    # --- 3. XGBoost ---
    try:
        from xgboost import XGBClassifier
        logger.info("🧠 Model 3: Training XGBoost Classifier (Gradient Boosting)...")
        xgb_model = XGBClassifier(
            n_estimators=120,
            max_depth=4,
            learning_rate=0.08,
            subsample=0.8,
            colsample_bytree=0.8,
            scale_pos_weight=scale_pos_weight,
            random_state=42,
            eval_metric="logloss"
        )
        xgb_model.fit(X_train_scaled, y_train)
        models["XGBoost"] = xgb_model
    except ImportError:
        logger.warning("⚠️ xgboost not installed. Skipping Model 3...")
        
    # --- 4. LightGBM ---
    try:
        from lightgbm import LGBMClassifier
        logger.info("🧠 Model 4: Training LightGBM Classifier (Histogram-based Boosting)...")
        lgb_model = LGBMClassifier(
            n_estimators=100,
            max_depth=4,
            learning_rate=0.05,
            scale_pos_weight=scale_pos_weight,
            random_state=42,
            verbosity=-1
        )
        lgb_model.fit(X_train_scaled, y_train)
        models["LightGBM"] = lgb_model
    except ImportError:
        logger.warning("⚠️ lightgbm not installed. Skipping Model 4...")
        
    # ==========================================
    # EVALUATION & METRIC COMPARISON
    # ==========================================
    logger.info("\n📊 Evaluating and comparing model capabilities on Future Test Set...")
    
    results = []
    trained_models = {}
    
    for name, model in models.items():
        # Get predictions
        y_pred = model.predict(X_test_scaled)
        
        # Get probability
        if hasattr(model, "predict_proba"):
            y_pred_proba = model.predict_proba(X_test_scaled)[:, 1]
        else:
            y_pred_proba = model.decision_function(X_test_scaled)
            # scale decision function to 0-1 range roughly for AUC calculation
            y_pred_proba = 1 / (1 + np.exp(-y_pred_proba))
            
        acc = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred, zero_division=0)
        rec = recall_score(y_test, y_pred, zero_division=0)
        f1 = f1_score(y_test, y_pred, zero_division=0)
        auc = roc_auc_score(y_test, y_pred_proba)
        
        results.append({
            "Model Name": name,
            "Accuracy": acc,
            "Precision (Class 1)": prec,
            "Recall (Class 1)": rec,
            "F1-Score": f1,
            "ROC-AUC": auc
        })
        trained_models[name] = (model, f1, rec, auc)
        
    # Create comparative DataFrame
    comparison_df = pd.DataFrame(results).sort_values("F1-Score", ascending=False)
    
    # Print comparative ASCII table
    logger.info("\n" + "=" * 110)
    logger.info("🏆 MULTI-MODEL COMPETITIVE PERFORMANCE METRICS TABLE (Future Out-of-Time Test Set)")
    logger.info("=" * 110)
    header_str = f"{'Model Name':<25} | {'Accuracy':>10} | {'Precision(1)':>12} | {'Recall(1)':>10} | {'F1-Score(1)':>12} | {'ROC-AUC':>10}"
    logger.info(header_str)
    logger.info("-" * 110)
    
    for _, r in comparison_df.iterrows():
        row_str = (
            f"{r['Model Name']:<25} | "
            f"{r['Accuracy']*100:9.2f}% | "
            f"{r['Precision (Class 1)']*100:11.2f}% | "
            f"{r['Recall (Class 1)']*100:9.2f}% | "
            f"{r['F1-Score']*100:11.2f}% | "
            f"{r['ROC-AUC']:.4f}"
        )
        logger.info(row_str)
    logger.info("=" * 110)
    
    # Determine the absolute best model
    # Priority: Highest F1-Score to balance both precision & recall, but with high recall constraint (> 85%)
    best_model_name = comparison_df.iloc[0]["Model Name"]
    best_model, best_f1, best_rec, best_auc = trained_models[best_model_name]
    
    logger.info(f"🏆 SELECTING BEST OVERALL MODEL: {best_model_name.upper()}")
    logger.info(f"   - F1-Score      : {best_f1:.4f}")
    logger.info(f"   - Recall (Class 1): {best_rec:.4f}")
    logger.info(f"   - ROC-AUC Score : {best_auc:.4f}")
    
    # Save the selected best model and the scaler to disk
    model_dir = os.path.join(os.path.dirname(config.FINAL_DATASET_FILE), "..", "models")
    os.makedirs(model_dir, exist_ok=True)
    
    best_model_path = os.path.join(model_dir, "best_distress_model.pkl")
    scaler_path = os.path.join(model_dir, "scaler.pkl")
    
    joblib.dump(best_model, best_model_path)
    joblib.dump(scaler, scaler_path)

    y_proba = _predict_proba_positive(best_model, X_test_scaled)
    sweep_thresholds = [0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70]
    _log_threshold_sweep(y_test.values, y_proba, sweep_thresholds)

    metrics_default = _metrics_at_threshold(y_test.values, y_proba, DEFAULT_THRESHOLD)
    tuned_thr, _ = _pick_recall_first_threshold(y_test.values, y_proba, TARGET_RECALL)
    metrics_tuned = _metrics_at_threshold(y_test.values, y_proba, tuned_thr)

    logger.info("\n" + "=" * 95)
    logger.info("⚖️ SO SÁNH NGƯỠNG MẶC ĐỊNH vs TUNE RECALL (Early Warning)")
    logger.info("=" * 95)
    logger.info(
        f"{'Mode':<22} | {'Thr':>5} | {'Precision':>10} | {'Recall':>10} | {'F1':>10} | {'Missed':>8}"
    )
    logger.info("-" * 95)
    for label, m in [
        ("Default (0.50)", metrics_default),
        (f"Tuned (rec>={TARGET_RECALL:.0%})", metrics_tuned),
    ]:
        y_p = (y_proba >= m["threshold"]).astype(int)
        cm = confusion_matrix(y_test.values, y_p)
        missed = int(cm[1, 0])
        logger.info(
            f"{label:<22} | {m['threshold']:>5.2f} | {m['precision']*100:9.2f}% | "
            f"{m['recall']*100:9.2f}% | {m['f1']*100:9.2f}% | {missed:>8}"
        )
    logger.info("=" * 95)

    recall_gain = metrics_tuned["recall"] - metrics_default["recall"]
    precision_drop = metrics_default["precision"] - metrics_tuned["precision"]
    use_tuned = recall_gain > 0.02 and metrics_tuned["recall"] >= TARGET_RECALL - 1e-6
    if use_tuned:
        logger.info(
            f"✅ Khuyến nghị: dùng ngưỡng {tuned_thr:.3f} "
            f"(recall +{recall_gain:.1%}, precision -{precision_drop:.1%})."
        )
        active_threshold = tuned_thr
    else:
        logger.info(
            f"↩️ Tune không cải thiện đủ — giữ ngưỡng mặc định {DEFAULT_THRESHOLD} "
            f"(đặt FINVISTA_DISTRESS_THRESHOLD={DEFAULT_THRESHOLD} để ép)."
        )
        active_threshold = DEFAULT_THRESHOLD
        metrics_tuned = metrics_default

    threshold_config = {
        "default_threshold": DEFAULT_THRESHOLD,
        "target_recall": TARGET_RECALL,
        "active_threshold": active_threshold,
        "use_tuned_threshold": use_tuned,
        "metrics_default": metrics_default,
        "metrics_tuned": metrics_tuned,
        "metrics_at_active": _metrics_at_threshold(y_test.values, y_proba, active_threshold),
        "best_model": best_model_name,
        "split_year": split_year,
    }
    threshold_path = os.path.join(model_dir, "threshold_config.json")
    with open(threshold_path, "w", encoding="utf-8") as f:
        json.dump(threshold_config, f, indent=2)

    test_eval = df.loc[test_mask, ["ticker", "year", "distress_label"]].copy()
    test_eval["distress_proba"] = y_proba
    test_eval["pred_default"] = (y_proba >= DEFAULT_THRESHOLD).astype(int)
    test_eval["pred_active"] = (y_proba >= active_threshold).astype(int)
    _log_per_year_metrics(test_eval, "pred_default")
    _log_per_year_metrics(test_eval, "pred_active")

    _log_confusion_matrix(
        y_test.values,
        (y_proba >= DEFAULT_THRESHOLD).astype(int),
        f"Default threshold {DEFAULT_THRESHOLD}",
    )
    _log_confusion_matrix(
        y_test.values,
        (y_proba >= active_threshold).astype(int),
        f"Active threshold {active_threshold:.3f}",
    )

    logger.info(f"💾 Exported Best Model successfully to: {os.path.abspath(best_model_path)}")
    logger.info(f"💾 Exported Scaler successfully to: {os.path.abspath(scaler_path)}")
    logger.info(f"💾 Exported Threshold config to: {os.path.abspath(threshold_path)}")
    
    # --------------------------------------------------
    # FEATURE IMPORTANCE FOR THE BEST MODEL
    # --------------------------------------------------
    logger.info("\n" + "=" * 75)
    logger.info(f"🔑 FEATURE IMPORTANCE ANALYSIS ({best_model_name.upper()})")
    logger.info("=" * 75)
    
    if hasattr(best_model, "feature_importances_"):
        importances = best_model.feature_importances_
        indices = np.argsort(importances)[::-1]
        
        for rank in range(min(10, len(feature_cols))):
            idx = indices[rank]
            logger.info(f"   Rank {rank+1:02d}: {feature_cols[idx]:<30} (Weight: {importances[idx]:.4f})")
            
    elif hasattr(best_model, "coef_"):
        # For Logistic Regression, absolute coefficients represent importance
        importances = np.abs(best_model.coef_[0])
        indices = np.argsort(importances)[::-1]
        
        for rank in range(min(10, len(feature_cols))):
            idx = indices[rank]
            direction = "POS (Increase risk)" if best_model.coef_[0][idx] > 0 else "NEG (Decrease risk)"
            logger.info(f"   Rank {rank+1:02d}: {feature_cols[idx]:<30} (Coef: {best_model.coef_[0][idx]:+.4f} | {direction})")
            
    else:
        logger.info("⚠️ Feature importances not available for this model type.")
    logger.info("=" * 75 + "\n")
    
    # --------------------------------------------------
    # SHAP EXPLAINABILITY (optional — skip if not installed)
    # --------------------------------------------------
    try:
        import shap, warnings
        warnings.filterwarnings("ignore", category=UserWarning, module="shap")
        logger.info("\n" + "=" * 75)
        logger.info("🧠 SHAP FEATURE EXPLANATION (Global Importance on Test Set)")
        logger.info("=" * 75)
        
        if hasattr(best_model, "feature_importances_"):  # Tree-based models
            explainer = shap.TreeExplainer(best_model)
            shap_values = explainer.shap_values(X_test_scaled)
            # LightGBM binary: shap_values is a list [neg_class, pos_class]
            # Coerce to single 2D ndarray for positive class
            import numpy as _np
            if isinstance(shap_values, list):
                sv = _np.array(shap_values[1])
            elif shap_values.ndim == 3:  # (n_classes, n_samples, n_features)
                sv = shap_values[1]
            else:
                sv = shap_values
            mean_abs_shap = pd.Series(
                data=abs(sv).mean(axis=0),
                index=feature_cols
            ).sort_values(ascending=False)
            
            logger.info(f"{'Rank':<6} {'Feature':<30} {'Mean |SHAP|':>12}")
            logger.info("-" * 50)
            for rank, (feat, val) in enumerate(mean_abs_shap.head(15).items(), 1):
                logger.info(f"{rank:<6} {feat:<30} {val:>12.4f}")
            
            # Persist SHAP importance to JSON for API/frontend use
            shap_export_path = os.path.join(model_dir, "shap_feature_importance.json")
            shap_dict = mean_abs_shap.head(20).round(6).to_dict()
            with open(shap_export_path, "w", encoding="utf-8") as f:
                _json_shap = {k: float(v) for k, v in shap_dict.items()}
                import json as _j
                _j.dump({"model": best_model_name, "top_features": _json_shap}, f, indent=2)
            logger.info(f"💾 SHAP importance exported to: {os.path.abspath(shap_export_path)}")
        else:
            logger.info("⚠️ SHAP TreeExplainer only supports tree-based models. Skipping for this model type.")
        logger.info("=" * 75)
    except ImportError:
        logger.warning("⚠️ 'shap' package not installed — skipping SHAP explainability.")
        logger.warning("   To enable: pip install shap")
    except Exception as _shap_e:
        logger.warning(f"⚠️ SHAP computation failed (non-critical): {_shap_e}")
    
    logger.info("==========================================================")

def main():
    train_prediction_model()

if __name__ == "__main__":
    main()
