# -*- coding: utf-8 -*-
"""Multi-model training: a diverse classifier zoo for comparison."""

import os
from typing import Any, Dict

import pandas as pd
from sklearn.model_selection import GroupKFold, RandomizedSearchCV
from sklearn.ensemble import ExtraTreesClassifier, GradientBoostingClassifier, HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.svm import LinearSVC

from src.core.utils import logger
from src.modules.credit_risk.models.credit_risk_preprocessor import PreparedDataset


def _maybe_tune_models(models: Dict[str, Any], prepared: PreparedDataset) -> Dict[str, Any]:
    """
    Optional hyperparameter tuning using GroupKFold by year to avoid time leakage.

    Enable via: FINVISTA_TUNE=1
    """
    if os.getenv("FINVISTA_TUNE", "0") != "1":
        return models

    X = prepared.X_train_scaled
    y = prepared.y_train
    years = prepared.train_years

    unique_years = sorted(set(int(v) for v in years))
    if len(unique_years) < 3:
        logger.warning("⚠️ Not enough years for tuning CV. Skipping FINVISTA_TUNE.")
        return models

    n_splits = min(5, len(unique_years))
    cv = GroupKFold(n_splits=n_splits)
    logger.info(f"🧪 Hyperparameter tuning enabled (GroupKFold by year, n_splits={n_splits}).")

    tuned: Dict[str, Any] = dict(models)

    def _run(name: str, estimator: Any, param_distributions: Dict[str, Any], n_iter: int = 20) -> None:
        logger.info(f"🔧 Tuning {name} (random search, n_iter={n_iter})...")
        search = RandomizedSearchCV(
            estimator=estimator,
            param_distributions=param_distributions,
            n_iter=n_iter,
            scoring="f1",
            cv=cv,
            n_jobs=-1,
            random_state=42,
            verbose=0,
        )
        search.fit(X, y, groups=years)
        tuned[name] = search.best_estimator_
        logger.info(f"✅ Tuned {name}: best_f1_cv={search.best_score_:.4f} | best_params={search.best_params_}")

    # Focus tuning budget on the best-performing / most promising models
    base_iter = int(os.getenv("FINVISTA_TUNE_NITER", "20"))
    boost_iter = int(os.getenv("FINVISTA_TUNE_NITER_BOOST", str(max(10, base_iter))))

    if "HistGradientBoosting" in models:
        _run(
            "HistGradientBoosting",
            models["HistGradientBoosting"],
            {
                "learning_rate": [0.01, 0.03, 0.05, 0.08, 0.1],
                "max_depth": [3, 4, 5, 6, 8, None],
                "max_leaf_nodes": [15, 31, 63, 127],
                "min_samples_leaf": [10, 20, 30, 50, 80],
                "l2_regularization": [0.0, 0.1, 0.5, 1.0, 2.0],
                "max_bins": [128, 255],
            },
            n_iter=max(10, base_iter),
        )

    if "Random Forest" in models:
        _run(
            "Random Forest",
            models["Random Forest"],
            {
                "n_estimators": [200, 400, 600],
                "max_depth": [4, 6, 8, 10, None],
                "min_samples_leaf": [1, 2, 5, 10, 20],
                "max_features": ["sqrt", "log2", None, 0.5, 0.8],
            },
            n_iter=max(10, base_iter),
        )

    if "Logistic Regression" in models:
        _run(
            "Logistic Regression",
            models["Logistic Regression"],
            {
                "C": [0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0],
            },
            n_iter=min(10, base_iter),
        )

    # Optional tuning for boosted tree libraries (usually strongest on tabular).
    # Enable via FINVISTA_TUNE_BOOST=1 (in addition to FINVISTA_TUNE=1)
    if os.getenv("FINVISTA_TUNE_BOOST", "0") == "1":
        if "XGBoost" in models:
            _run(
                "XGBoost",
                models["XGBoost"],
                {
                    "n_estimators": [200, 400, 700],
                    "max_depth": [3, 4, 5, 6],
                    "learning_rate": [0.01, 0.03, 0.05, 0.08],
                    "subsample": [0.7, 0.8, 0.9, 1.0],
                    "colsample_bytree": [0.7, 0.8, 0.9, 1.0],
                    "min_child_weight": [1, 3, 5, 10],
                    "reg_lambda": [0.5, 1.0, 2.0, 5.0],
                },
                n_iter=max(10, boost_iter),
            )

        if "LightGBM" in models:
            _run(
                "LightGBM",
                models["LightGBM"],
                {
                    "n_estimators": [300, 600, 900],
                    "max_depth": [-1, 3, 4, 5, 6],
                    "learning_rate": [0.01, 0.03, 0.05, 0.08],
                    "num_leaves": [15, 31, 63, 127],
                    "min_child_samples": [10, 20, 30, 50, 80],
                    "subsample": [0.7, 0.8, 0.9, 1.0],
                    "colsample_bytree": [0.7, 0.8, 0.9, 1.0],
                    "reg_lambda": [0.0, 0.5, 1.0, 2.0, 5.0],
                },
                n_iter=max(10, boost_iter),
            )

    return tuned


def train_all_models(prepared: PreparedDataset) -> Dict[str, Any]:
    """Fit all candidate classifiers on scaled training data."""
    X_train_scaled = prepared.X_train_scaled
    y_train = prepared.y_train
    scale_pos_weight = prepared.scale_pos_weight

    # --- FINVISTA INSTITUTIONAL UPGRADE: SMOTE (Synthetic Minority Over-sampling) ---
    try:
        from imblearn.over_sampling import SMOTE
        logger.info("🧠 Applying SMOTE to handle highly imbalanced credit risk data...")
        smote = SMOTE(random_state=42)
        X_train_scaled, y_train = smote.fit_resample(X_train_scaled, y_train)
        scale_pos_weight = 1.0  # Reset because data is now perfectly balanced
        logger.info(f"✅ SMOTE applied successfully. New balanced shape: {X_train_scaled.shape}")
    except ImportError:
        logger.warning("⚠️ imbalanced-learn not installed. Proceeding with scale_pos_weight instead of SMOTE.")

    models: Dict[str, Any] = {}

    logger.info("🧠 Model 1: Training Logistic Regression (L2 penalty)...")
    lr_model = LogisticRegression(
        C=0.5,
        class_weight="balanced",
        max_iter=1000,
        random_state=42,
    )
    lr_model.fit(X_train_scaled, y_train)
    models["Logistic Regression"] = lr_model

    logger.info("🧠 Model 2: Training Random Forest (Bagging Ensemble)...")
    rf_model = RandomForestClassifier(
        n_estimators=100,
        max_depth=6,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )
    rf_model.fit(X_train_scaled, y_train)
    models["Random Forest"] = rf_model

    logger.info("🧠 Model 3: Training ExtraTrees (Randomized Trees Ensemble)...")
    et_model = ExtraTreesClassifier(
        n_estimators=300,
        max_depth=10,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )
    et_model.fit(X_train_scaled, y_train)
    models["ExtraTrees"] = et_model

    logger.info("🧠 Model 4: Training GradientBoosting (Classic GBDT)...")
    gb_model = GradientBoostingClassifier(
        random_state=42,
    )
    gb_model.fit(X_train_scaled, y_train)
    models["GradientBoosting"] = gb_model

    logger.info("🧠 Model 5: Training HistGradientBoosting (Fast GBDT)...")
    hgb_model = HistGradientBoostingClassifier(
        max_depth=6,
        learning_rate=0.05,
        random_state=42,
    )
    hgb_model.fit(X_train_scaled, y_train)
    models["HistGradientBoosting"] = hgb_model

    logger.info("🧠 Model 6: Training LinearSVC (Margin-based baseline)...")
    # Note: LinearSVC has decision_function (we convert to pseudo-probability downstream).
    # We rely on class_weight to handle imbalance.
    lsvm_model = LinearSVC(
        C=1.0,
        class_weight="balanced",
        random_state=42,
        max_iter=5000,
    )
    lsvm_model.fit(X_train_scaled, y_train)
    models["LinearSVC"] = lsvm_model

    logger.info("🧠 Model 7: Training GaussianNB (Fast probabilistic baseline)...")
    gnb_model = GaussianNB()
    gnb_model.fit(X_train_scaled, y_train)
    models["GaussianNB"] = gnb_model

    logger.info("🧠 Model 8: Training KNN (Local similarity baseline)...")
    knn_model = KNeighborsClassifier(
        n_neighbors=25,
        weights="distance",
        n_jobs=-1,
    )
    knn_model.fit(X_train_scaled, y_train)
    models["KNN"] = knn_model

    try:
        from xgboost import XGBClassifier

        logger.info("🧠 Model 9: Training XGBoost Classifier (Gradient Boosting)...")
        xgb_model = XGBClassifier(
            n_estimators=120,
            max_depth=4,
            learning_rate=0.08,
            subsample=0.8,
            colsample_bytree=0.8,
            scale_pos_weight=scale_pos_weight,
            random_state=42,
            eval_metric="logloss",
        )
        xgb_model.fit(X_train_scaled, y_train)
        models["XGBoost"] = xgb_model
    except ImportError:
        logger.warning("⚠️ xgboost not installed. Skipping Model 3...")

    try:
        from lightgbm import LGBMClassifier

        logger.info("🧠 Model 10: Training LightGBM Classifier (Histogram-based Boosting)...")
        lgb_model = LGBMClassifier(
            n_estimators=100,
            max_depth=4,
            learning_rate=0.05,
            scale_pos_weight=scale_pos_weight,
            random_state=42,
            verbosity=-1,
        )
        lgb_model.fit(X_train_scaled, y_train)
        models["LightGBM"] = lgb_model
    except ImportError:
        logger.warning("⚠️ lightgbm not installed. Skipping Model 4...")

    # Optional: CatBoost (often strong on tabular data) — keep optional to avoid heavy deps.
    try:
        from catboost import CatBoostClassifier
        from src.core import config

        logger.info("🧠 Model 11: Training CatBoost Classifier (Optional, strong on tabular)...")
        cb_model = CatBoostClassifier(
            iterations=400,
            depth=6,
            learning_rate=0.05,
            loss_function="Logloss",
            verbose=False,
            random_seed=42,
            train_dir=os.path.join(config.LOG_DIR, "catboost_info")
        )
        cb_model.fit(X_train_scaled, y_train)
        models["CatBoost"] = cb_model
    except ImportError:
        logger.info("ℹ️ catboost not installed. Skipping CatBoost (optional).")

    tuned_models = _maybe_tune_models(models, prepared)
    
    # --- FINVISTA 2.0: ENSEMBLE ARCHITECTURE (Stacking & Voting) ---
    # We now promote Stacking Ensemble as the core "Finvista 2.0" engine.
    # Enable by default unless explicitly disabled via FINVISTA_USE_ENSEMBLE=0
    if os.getenv("FINVISTA_USE_ENSEMBLE", "1") == "1":
        from sklearn.ensemble import StackingClassifier, VotingClassifier
        
        # Select the top-performing base learners for the ensemble
        # HistGradientBoosting, XGBoost, LightGBM, and CatBoost are the 'Big Four' for tabular data.
        core_estimators = []
        for name in ["HistGradientBoosting", "XGBoost", "LightGBM", "Random Forest", "CatBoost"]:
            if name in tuned_models:
                core_estimators.append((name.replace(" ", "_"), tuned_models[name]))
                
        if len(core_estimators) >= 3:
            logger.info(f"🧠 FINVISTA 2.0: Constructing Triple-Stacking Ensemble (Meta-Learner: Calibrated LR) of: {[e[0] for e in core_estimators]}...")
            
            # Stacking with a balanced meta-learner
            stacking_ensemble = StackingClassifier(
                estimators=core_estimators,
                final_estimator=LogisticRegression(
                    C=1.0, 
                    class_weight="balanced", 
                    solver="lbfgs",
                    random_state=42
                ),
                cv=5, # Internal 5-fold CV for meta-features
                n_jobs=-1,
                passthrough=False # Use only base model predictions for meta-learner
            )
            stacking_ensemble.fit(X_train_scaled, y_train)
            tuned_models["StackingEnsemble_V2"] = stacking_ensemble
            
            logger.info("🧠 FINVISTA 2.0: Constructing Soft-Voting Ensemble (Consensus Engine)...")
            voting_ensemble = VotingClassifier(
                estimators=core_estimators,
                voting="soft",
                n_jobs=-1
            )
            voting_ensemble.fit(X_train_scaled, y_train)
            tuned_models["VotingEnsemble_V2"] = voting_ensemble
        else:
            logger.warning("⚠️ Not enough high-quality base models to form a robust Stacking Ensemble. Skipping Phase 2.")
    else:
        logger.info("ℹ️ Progressive Modeling: Ensembles disabled via FINVISTA_USE_ENSEMBLE=0")
        
    return tuned_models
