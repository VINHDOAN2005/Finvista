# -*- coding: utf-8 -*-
"""
Main Pipeline Orchestrator for the Financial Distress Prediction System.
Runs Steps 1 through 5 in order to generate the finalized dataset.
"""

import time
from src.common.utils import logger
from src.common import config

def run_full_pipeline():
    start_time = time.time()
    
    logger.info("==========================================================")
    logger.info("🚀 STARTING FINANCIAL DISTRESS DATA ENGINEERING PIPELINE")
    logger.info("==========================================================")
    
    # Step 1: Filter listed companies
    from src.credit_risk.pipeline.step1_filter_companies import filter_companies
    tickers = filter_companies()
    
    if not tickers:
        logger.error("❌ Step 1 failed: No tickers available to crawl. Exiting...")
        return
        
    # Step 2: Resilient Crawler (runs crawler or simulator)
    from src.credit_risk.pipeline.step2_crawl_financials import crawl_financials
    # In a full production run, this collects data for all tickers
    # (For a quick test, you can reduce crawl pool size in config.py or skip if cached)
    crawl_financials(tickers)
    
    # Step 2.5: Structuring raw JSON data into CSV
    from src.credit_risk.helpers.filter_raw_data import filter_and_clean_raw_data
    success_clean = filter_and_clean_raw_data()
    if not success_clean:
        logger.error("❌ Data cleaning and structuring failed. Exiting...")
        return
        
    # Quality Audit Report (completeness check)
    from src.credit_risk.helpers.inspect_raw_data import inspect_raw_columns
    inspect_raw_columns()
    
    # Step 3: Compute Financial ratios & features
    from src.credit_risk.pipeline.step3_compute_features import compute_financial_features
    success_features = compute_financial_features()
    if not success_features:
        logger.error("❌ Feature computation failed. Exiting...")
        return
        
    # Step 4: Label financial distress status
    from src.credit_risk.pipeline.step4_label_distress import label_financial_distress
    success_label = label_financial_distress()
    if not success_label:
        logger.error("❌ Distress labeling failed. Exiting...")
        return
        
    # Step 5: Export final training-ready dataset
    from src.credit_risk.pipeline.step5_export_dataset import export_final_dataset
    success_export = export_final_dataset()
    if not success_export:
        logger.error("❌ Final dataset export failed. Exiting...")
        return
        
    elapsed_time = time.time() - start_time
    logger.info("==========================================================")
    logger.info(f"🎉 PIPELINE COMPLETED SUCCESSFULLY IN {elapsed_time/60:.2f} MINUTES!")
    logger.info(f"👉 Final dataset is ready for training: {config.FINAL_DATASET_FILE}")
    logger.info(f"👉 You can now run: python run_credit_risk.py --train to train XGBoost!")
    logger.info("==========================================================")

if __name__ == "__main__":
    run_full_pipeline()
