# -*- coding: utf-8 -*-
"""
Step 4: Label Financial Distress status.
Applies rule-based economic logic to tag distressed (1) vs healthy (0) companies.
"""

import os
import pandas as pd
import numpy as np
from src.common.utils import logger, load_csv, save_csv
from src.common import config

def label_financial_distress():
    logger.info("🎬 STEP 4: Labeling financial distress status...")
    
    if not os.path.exists(config.FEATURES_FILE):
        logger.error(f"❌ Financial features not found: {config.FEATURES_FILE}")
        return False
        
    df = load_csv(config.FEATURES_FILE)
    if df.empty:
        logger.error("❌ Features dataset is empty!")
        return False
        
    # Ensure sorted order for lag computations
    df.sort_values(by=["ticker", "year"], inplace=True)
    
    # Initialize labels
    df["distress_label"] = 0
    
    # Track criteria stats for analytical reporting
    criteria_hits = {
        "negative_equity": 0,
        "consecutive_losses_2y": 0,
        "consecutive_negative_ocf_3y": 0,
        "severe_liquidity_crisis": 0,
        "icr_below_one": 0,
        "total_distressed": 0
    }
    
    # We iterate by ticker to compute consecutive conditions safely
    for ticker, group in df.groupby("ticker"):
        # Check condition 1: Negative Equity (Vốn chủ sở hữu âm)
        neg_equity_mask = group["total_equity"] < 0
        df.loc[group.index[neg_equity_mask], "distress_label"] = 1
        criteria_hits["negative_equity"] += neg_equity_mask.sum()
        
        # Check condition 2: 2 Consecutive Years of Net Loss (Lỗ ròng 2 năm liên tiếp)
        if len(group) >= 2:
            loss_this_year = group["profit_after_tax"] < 0
            loss_prev_year = group["profit_after_tax"].shift(1) < 0
            consecutive_loss_mask = loss_this_year & loss_prev_year
            df.loc[group.index[consecutive_loss_mask], "distress_label"] = 1
            criteria_hits["consecutive_losses_2y"] += consecutive_loss_mask.sum()
            
        # Check condition 3: 3 Consecutive Years of Negative Operating Cash Flow (Dòng tiền HĐKD âm 3 năm liên tiếp)
        if len(group) >= 3:
            ocf_this_year = group["operating_cash_flow"] < 0
            ocf_prev_year_1 = group["operating_cash_flow"].shift(1) < 0
            ocf_prev_year_2 = group["operating_cash_flow"].shift(2) < 0
            consecutive_ocf_mask = ocf_this_year & ocf_prev_year_1 & ocf_prev_year_2
            df.loc[group.index[consecutive_ocf_mask], "distress_label"] = 1
            criteria_hits["consecutive_negative_ocf_3y"] += consecutive_ocf_mask.sum()
            
        # Check condition 4: Severe Liquidity Crisis (Hệ số thanh toán hiện thời < 0.5)
        liquidity_crisis_mask = group["current_ratio"] < 0.5
        df.loc[group.index[liquidity_crisis_mask], "distress_label"] = 1
        criteria_hits["severe_liquidity_crisis"] += liquidity_crisis_mask.sum()
        
        # Check condition 5: ICR < 1 (Không đủ EBIT để trả lãi vay — dấu hiệu sớm nhất)
        # icr column is guaranteed to exist from step3; cap extreme safe values at 9999
        if "icr" in group.columns:
            icr_crisis_mask = (group["icr"] < 1.0) & (group["icr"] != 9999.0)
            df.loc[group.index[icr_crisis_mask], "distress_label"] = 1
            criteria_hits["icr_below_one"] += icr_crisis_mask.sum()

    total_distressed = (df["distress_label"] == 1).sum()
    criteria_hits["total_distressed"] = total_distressed
    
    logger.info("📊 Financial Distress Labeling Statistics:")
    logger.info(f"   - Total records labeled: {len(df)}")
    logger.info(f"   - Distressed records (1): {total_distressed} ({total_distressed/len(df):.2%})")
    logger.info(f"   - Healthy records (0)   : {len(df) - total_distressed} ({(len(df)-total_distressed)/len(df):.2%})")
    logger.info("📍 Breaking down rule triggers:")
    logger.info(f"     * Negative Equity cases            : {criteria_hits['negative_equity']}")
    logger.info(f"     * 2-Year Consecutive Net Losses    : {criteria_hits['consecutive_losses_2y']}")
    logger.info(f"     * 3-Year Consecutive Negative OCF  : {criteria_hits['consecutive_negative_ocf_3y']}")
    logger.info(f"     * Severe Liquidity crisis (<0.5)   : {criteria_hits['severe_liquidity_crisis']}")
    logger.info(f"     * ICR < 1 (Cannot cover interest)  : {criteria_hits['icr_below_one']}")
    
    # Cross-validate rule-based labels against Springate & Zmijewski models
    if "springate_distressed" in df.columns:
        agreement_s = (df["distress_label"] == df["springate_distressed"]).mean()
        logger.info(f"   🔀 Springate agreement with rule labels: {agreement_s:.2%}")
    if "zmijewski_distressed" in df.columns:
        agreement_z = (df["distress_label"] == df["zmijewski_distressed"]).mean()
        logger.info(f"   🔀 Zmijewski agreement with rule labels: {agreement_z:.2%}")
    
    # Save labeled dataset
    save_csv(df, config.LABELED_DATA_FILE)
    logger.info(f"✅ Labeled dataset saved to {config.LABELED_DATA_FILE}")
    return True

def main():
    label_financial_distress()

if __name__ == "__main__":
    main()
