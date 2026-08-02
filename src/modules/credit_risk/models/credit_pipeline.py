# -*- coding: utf-8 -*-
"""
🚀 FINVISTA CREDIT RISK PIPELINE — ORCHESTRATOR (Steps 1–5)
============================================================
Điều phối toàn bộ pipeline thu thập và xử lý dữ liệu tài chính theo thứ tự
Step 1 → 5 để tạo ra dataset huấn luyện sẵn sàng cho Step 6 (ML Training).

Luồng xử lý:
  Step 1 · Filter    → Lọc danh sách mã niêm yết đủ điều kiện
  Step 2 · Crawl     → Cào BCTC (BS, IS, CF) kiên cường với Retry & Checkpoint
  Step 2.5 · Clean   → Chuẩn hóa cột, quy đổi đơn vị, loại trùng lặp
  Step 3 · Features  → Tính 25+ chỉ số tài chính (Liquidity, Leverage, Growth…)
  Step 4 · Label     → Gán nhãn Altman Z''-Score & Rule-based Distress
  Step 5 · Export    → Xuất final_processed_dataset.csv cho ML

CLI: python run.py credit
"""

import time
from src.core.utils import logger
from src.core import config


def run_full_pipeline():
    start_time = time.time()

    logger.info("🚀 STARTING FINANCIAL DISTRESS DATA ENGINEERING PIPELINE (Steps 1–5)")

    # Step 1: Filter listed companies
    from src.modules.credit_risk.models.credit_step1_filter import filter_companies
    tickers = filter_companies()

    if not tickers:
        logger.error("❌ Step 1 failed: No tickers available to crawl. Exiting...")
        return

    # Step 2: Resilient Crawler
    from src.modules.credit_risk.models.credit_step2_crawl import crawl_financials
    crawl_financials(tickers)

    # Step 2.5: Structuring raw JSON data into CSV
    from src.modules.credit_risk.etl.filter_raw_data import filter_and_clean_raw_data
    success_clean = filter_and_clean_raw_data()
    if not success_clean:
        logger.error("❌ Data cleaning and structuring failed. Exiting...")
        return

    # Quality Audit Report (completeness check)
    from src.modules.credit_risk.etl.inspect_raw_data import inspect_raw_columns
    inspect_raw_columns()

    # Step 3: Compute Financial ratios & features
    from src.modules.credit_risk.models.credit_step3_compute_features import compute_financial_features
    success_features = compute_financial_features()
    if not success_features:
        logger.error("❌ Feature computation failed. Exiting...")
        return

    # Step 4: Label financial distress status
    from src.modules.credit_risk.models.credit_step4_label import label_financial_distress
    success_label = label_financial_distress()
    if not success_label:
        logger.error("❌ Distress labeling failed. Exiting...")
        return

    # Step 5: Export final training-ready dataset
    from src.modules.credit_risk.models.credit_step5_export import export_final_dataset
    success_export = export_final_dataset()
    if not success_export:
        logger.error("❌ Final dataset export failed. Exiting...")
        return

    elapsed_time = time.time() - start_time
    logger.info(f"🎉 PIPELINE STEPS 1–5 COMPLETED SUCCESSFULLY IN {elapsed_time/60:.2f} MINUTES!")
    logger.info(f"👉 Final dataset ready: {config.FINAL_DATASET_FILE}")
    logger.info("👉 Next: python run.py credit --train   (Step 6: Train ML Model)")


if __name__ == "__main__":
    run_full_pipeline()
