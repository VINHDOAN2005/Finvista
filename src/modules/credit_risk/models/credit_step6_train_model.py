# -*- coding: utf-8 -*-
"""
🏁 FINVISTA CREDIT RISK PIPELINE — STEP 6: TRAIN ML MODEL
=========================================================
Huấn luyện và so sánh 11+ mô hình học máy phân loại kiệt quệ tài chính.
Nạp dữ liệu từ Step 5, chia Train/Test theo thời gian (Time-Based Split),
huấn luyện, đánh giá và xuất mô hình tốt nhất ra file `.pkl`.

CLI: python run.py credit --train

Author: samvo
"""

from src.core.utils import logger
from src.modules.credit_risk.models.credit_risk_evaluator import evaluate_and_export
from src.modules.credit_risk.models.credit_risk_preprocessor import prepare_train_test_split
from src.modules.credit_risk.models.credit_risk_trainer import train_all_models


def train_prediction_model():
    logger.info("🏁 INITIALIZING ADVANCED MULTI-MODEL ML COMPARATIVE ENGINE")

    prepared = prepare_train_test_split()
    if prepared is None:
        return

    models = train_all_models(prepared)
    if not models:
        logger.error("❌ No models were trained successfully.")
        return

    evaluate_and_export(models, prepared)


def main():
    train_prediction_model()


if __name__ == "__main__":
    main()
