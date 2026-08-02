# -*- coding: utf-8 -*-
"""Model evaluation: metrics, threshold tuning, SHAP, and artifact export."""

import json
import os
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)

from src.core import config
from src.core.utils import logger
from src.modules.credit_risk.models.credit_risk_preprocessor import DEFAULT_THRESHOLD, PreparedDataset, TARGET_RECALL


def predict_proba_positive(model: Any, X: pd.DataFrame) -> np.ndarray:
    if hasattr(model, "predict_proba"):
        return model.predict_proba(X)[:, 1]
    scores = model.decision_function(X)
    return 1.0 / (1.0 + np.exp(-scores))


def metrics_at_threshold(y_true: np.ndarray, y_proba: np.ndarray, threshold: float) -> Dict[str, float]:
    y_pred = (y_proba >= threshold).astype(int)
    return {
        "threshold": threshold,
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
    }


def pick_recall_first_threshold(
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

    idx = int(np.argmax(recalls[:-1]))
    thr = float(thresholds[idx])
    return thr, metrics_at_threshold(y_true, y_proba, thr)


def log_threshold_sweep(y_true: np.ndarray, y_proba: np.ndarray, thresholds: List[float]) -> None:
    logger.info("\n" + "=" * 95)
    logger.info("📈 PRECISION / RECALL THEO NGƯỠNG (Out-of-Time Test Set)")
    logger.info("=" * 95)
    logger.info(
        f"{'Threshold':>10} | {'Precision':>10} | {'Recall':>10} | {'F1':>10} | {'Flagged':>8}"
    )
    logger.info("-" * 95)
    for thr in thresholds:
        m = metrics_at_threshold(y_true, y_proba, thr)
        flagged = int(np.sum(y_proba >= thr))
        logger.info(
            f"{m['threshold']:>10.2f} | {m['precision']*100:9.2f}% | {m['recall']*100:9.2f}% | "
            f"{m['f1']*100:9.2f}% | {flagged:>8}"
        )
    logger.info("=" * 95)


def log_per_year_metrics(test_df: pd.DataFrame, pred_col: str) -> None:
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


def log_confusion_matrix(y_true: np.ndarray, y_pred: np.ndarray, title: str) -> None:
    cm = confusion_matrix(y_true, y_pred)
    logger.info(f"\n📋 Confusion Matrix — {title}:")
    logger.info("   Dự đoán 0 | Dự đoán 1")
    logger.info(f"Thực tế 0:  {cm[0, 0]:<5} | {cm[0, 1]}")
    logger.info(f"Thực tế 1:  {cm[1, 0]:<5} | {cm[1, 1]}  <-- (Số bỏ sót: {cm[1, 0]})")


def evaluate_and_export(models: Dict[str, Any], prepared: PreparedDataset) -> None:
    """Compare models on the test set, export best model, scaler, and threshold config."""
    X_test_scaled = prepared.X_test_scaled
    y_test = prepared.y_test
    feature_cols = prepared.feature_cols
    scaler = prepared.scaler
    split_year = prepared.split_year
    df = prepared.df

    logger.info("\n📊 Evaluating and comparing model capabilities on Future Test Set...")

    results = []
    trained_models = {}

    for name, model in models.items():
        y_pred = model.predict(X_test_scaled)

        if hasattr(model, "predict_proba"):
            y_pred_proba = model.predict_proba(X_test_scaled)[:, 1]
        else:
            y_pred_proba = model.decision_function(X_test_scaled)
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
            "ROC-AUC": auc,
        })
        trained_models[name] = (model, f1, rec, auc)

    comparison_df = pd.DataFrame(results).sort_values("F1-Score", ascending=False)

    logger.info("\n" + "=" * 110)
    logger.info("🏆 MULTI-MODEL COMPETITIVE PERFORMANCE METRICS TABLE (Future Out-of-Time Test Set)")
    logger.info("=" * 110)
    header_str = (
        f"{'Model Name':<25} | {'Accuracy':>10} | {'Precision(1)':>12} | "
        f"{'Recall(1)':>10} | {'F1-Score(1)':>12} | {'ROC-AUC':>10}"
    )
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

    best_model_name = comparison_df.iloc[0]["Model Name"]
    best_model, best_f1, best_rec, best_auc = trained_models[best_model_name]

    logger.info(f"🏆 SELECTING BEST OVERALL MODEL: {best_model_name.upper()}")
    logger.info(f"   - F1-Score      : {best_f1:.4f}")
    logger.info(f"   - Recall (Class 1): {best_rec:.4f}")
    logger.info(f"   - ROC-AUC Score : {best_auc:.4f}")

    model_dir = config.MODELS_DIR
    os.makedirs(model_dir, exist_ok=True)

    best_model_path = config.BEST_DISTRESS_MODEL
    scaler_path = config.SCALER_ARTIFACT

    joblib.dump(best_model, best_model_path)
    joblib.dump(scaler, scaler_path)

    # Persist model hyperparameters for reproducibility (best-effort).
    try:
        params_path = os.path.join(model_dir, "best_model_params.json")
        params = best_model.get_params() if hasattr(best_model, "get_params") else {}
        with open(params_path, "w", encoding="utf-8") as f:
            json.dump({"model": best_model_name, "params": params}, f, indent=2, default=str)
        logger.info(f"💾 Exported Best Model params to: {os.path.abspath(params_path)}")
    except Exception as e:
        logger.warning(f"⚠️ Could not export best model params (non-critical): {e}")

    y_proba = predict_proba_positive(best_model, X_test_scaled)
    sweep_thresholds = [0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70]
    log_threshold_sweep(y_test.values, y_proba, sweep_thresholds)

    metrics_default = metrics_at_threshold(y_test.values, y_proba, DEFAULT_THRESHOLD)
    tuned_thr, _ = pick_recall_first_threshold(y_test.values, y_proba, TARGET_RECALL)
    metrics_tuned = metrics_at_threshold(y_test.values, y_proba, tuned_thr)

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
        "metrics_at_active": metrics_at_threshold(y_test.values, y_proba, active_threshold),
        "best_model": best_model_name,
        "split_year": split_year,
    }
    threshold_path = config.THRESHOLD_CONFIG
    with open(threshold_path, "w", encoding="utf-8") as f:
        json.dump(threshold_config, f, indent=2)

    test_mask = df["year"] > split_year
    test_eval = df.loc[test_mask, ["ticker", "year", "distress_label"]].copy()
    test_eval["distress_proba"] = y_proba
    test_eval["pred_default"] = (y_proba >= DEFAULT_THRESHOLD).astype(int)
    test_eval["pred_active"] = (y_proba >= active_threshold).astype(int)
    log_per_year_metrics(test_eval, "pred_default")
    log_per_year_metrics(test_eval, "pred_active")

    log_confusion_matrix(
        y_test.values,
        (y_proba >= DEFAULT_THRESHOLD).astype(int),
        f"Default threshold {DEFAULT_THRESHOLD}",
    )
    log_confusion_matrix(
        y_test.values,
        (y_proba >= active_threshold).astype(int),
        f"Active threshold {active_threshold:.3f}",
    )

    logger.info(f"💾 Exported Best Model successfully to: {os.path.abspath(best_model_path)}")
    logger.info(f"💾 Exported Scaler successfully to: {os.path.abspath(scaler_path)}")
    logger.info(f"💾 Exported Threshold config to: {os.path.abspath(threshold_path)}")

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
        importances = np.abs(best_model.coef_[0])
        indices = np.argsort(importances)[::-1]
        for rank in range(min(10, len(feature_cols))):
            idx = indices[rank]
            direction = "POS (Increase risk)" if best_model.coef_[0][idx] > 0 else "NEG (Decrease risk)"
            logger.info(
                f"   Rank {rank+1:02d}: {feature_cols[idx]:<30} "
                f"(Coef: {best_model.coef_[0][idx]:+.4f} | {direction})"
            )
    else:
        logger.info("⚠️ Feature importances not available for this model type.")
    logger.info("=" * 75 + "\n")

    _run_shap_analysis(best_model, best_model_name, X_test_scaled, feature_cols, model_dir)


def _extract_positive_class_shap(shap_values):
    if isinstance(shap_values, list):
        if len(shap_values) > 1:
            return np.array(shap_values[1])
        else:
            return np.array(shap_values[0])
    if isinstance(shap_values, np.ndarray):
        if shap_values.ndim == 3:
            if shap_values.shape[2] == 2:
                return shap_values[:, :, 1]
            elif shap_values.shape[0] == 2:
                return shap_values[1, :, :]
        return shap_values
    return shap_values


def _run_shap_analysis(best_model, best_model_name, X_test_scaled, feature_cols, model_dir):
    try:
        import json as _json
        import warnings

        import shap

        warnings.filterwarnings("ignore", category=UserWarning, module="shap")
        logger.info("\n" + "=" * 75)
        logger.info("🧠 SHAP FEATURE EXPLANATION (Global Importance on Test Set)")
        logger.info("=" * 75)

        is_ensemble = hasattr(best_model, "named_estimators_")
        mean_abs_shap = None

        if is_ensemble:
            logger.info(f"ℹ️ {best_model_name} detected. Calculating SHAP values across tree-based ensemble members...")
            all_shaps = []
            for name, est in best_model.named_estimators_.items():
                if name in ["XGBoost", "LightGBM", "CatBoost", "HistGradientBoosting", "Random Forest", "GradientBoosting"]:
                    try:
                        explainer = shap.TreeExplainer(est)
                        shap_values = explainer.shap_values(X_test_scaled)
                        sv = _extract_positive_class_shap(shap_values)
                        all_shaps.append(abs(sv).mean(axis=0))
                    except Exception as sub_e:
                        logger.warning(f"   * Could not calculate SHAP values for {name}: {sub_e}")
            if all_shaps:
                mean_abs_val = np.mean(all_shaps, axis=0)
                mean_abs_shap = pd.Series(
                    data=mean_abs_val,
                    index=feature_cols,
                ).sort_values(ascending=False)
        elif hasattr(best_model, "feature_importances_") or best_model_name in ["XGBoost", "LightGBM", "CatBoost", "HistGradientBoosting", "Random Forest", "GradientBoosting"]:
            explainer = shap.TreeExplainer(best_model)
            shap_values = explainer.shap_values(X_test_scaled)
            sv = _extract_positive_class_shap(shap_values)
            mean_abs_shap = pd.Series(
                data=abs(sv).mean(axis=0),
                index=feature_cols,
            ).sort_values(ascending=False)

        if mean_abs_shap is not None:
            logger.info(f"{'Rank':<6} {'Feature':<30} {'Mean |SHAP|':>12}")
            logger.info("-" * 50)
            for rank, (feat, val) in enumerate(mean_abs_shap.head(15).items(), 1):
                logger.info(f"{rank:<6} {feat:<30} {val:>12.4f}")

            shap_export_path = os.path.join(model_dir, "shap_feature_importance.json")
            shap_dict = mean_abs_shap.head(20).round(6).to_dict()
            with open(shap_export_path, "w", encoding="utf-8") as f:
                _json.dump(
                    {"model": best_model_name, "top_features": {k: float(v) for k, v in shap_dict.items()}},
                    f,
                    indent=2,
                )
            logger.info(f"💾 SHAP importance exported to: {os.path.abspath(shap_export_path)}")
        else:
            logger.info("⚠️ SHAP TreeExplainer only supports tree-based models. Skipping for this model type.")
        logger.info("=" * 75)
    except ImportError:
        logger.warning("⚠️ 'shap' package not installed — skipping SHAP explainability.")
        logger.warning("   To enable: pip install shap")
    except Exception as shap_e:
        logger.warning(f"⚠️ SHAP computation failed (non-critical): {shap_e}")
