# -*- coding: utf-8 -*-
"""
Inspection tool to analyze computed financial indicators, distribution stats, and outliers.
"""

import os
import pandas as pd
from src.common.utils import logger, load_csv
from src.common import config

def inspect_computed_features():
    logger.info("=============================================")
    logger.info("📊 ANALYZING COMPUTED FINANCIAL INDICATORS")
    logger.info("=============================================")
    
    if not os.path.exists(config.FEATURES_FILE):
        logger.error(f"❌ Features file not found: {config.FEATURES_FILE}")
        return False
        
    df = load_csv(config.FEATURES_FILE)
    if df.empty:
        logger.error("❌ Dataset is empty!")
        return False
        
    # Standard indicators to validate
    indicators = [
        "current_ratio", 
        "working_capital_to_assets", 
        "roa", 
        "roe", 
        "debt_ratio", 
        "altman_z_score"
    ]
    
    logger.info("📈 Descriptive Statistics for Key Features:")
    for ind in indicators:
        if ind in df.columns:
            median_val = df[ind].median()
            mean_val = df[ind].mean()
            min_val = df[ind].min()
            max_val = df[ind].max()
            
            logger.info(f"   🔹 {ind:<25}:")
            logger.info(f"      * Range  : [{min_val:.4f} to {max_val:.4f}]")
            logger.info(f"      * Mean   : {mean_val:.4f}")
            logger.info(f"      * Median : {median_val:.4f}")
            
    # Z-Score Classification inspection
    if "altman_z_score" in df.columns:
        logger.info("\n🚩 Altman Z''-Score Zone Distribution:")
        distressed_zone = (df["altman_z_score"] < 1.1).sum()
        grey_zone = ((df["altman_z_score"] >= 1.1) & (df["altman_z_score"] <= 2.6)).sum()
        safe_zone = (df["altman_z_score"] > 2.6).sum()
        total = len(df)
        
        logger.info(f"   🔴 Distress/Danger Zone (< 1.1) : {distressed_zone:>4} ({distressed_zone/total:.2%})")
        logger.info(f"   🟡 Warning/Grey Zone (1.1-2.6) : {grey_zone:>4} ({grey_zone/total:.2%})")
        logger.info(f"   🟢 Safe Zone (> 2.6)           : {safe_zone:>4} ({safe_zone/total:.2%})")
        
    logger.info("=============================================")
    return True

def main():
    inspect_computed_features()

if __name__ == "__main__":
    main()
