# -*- coding: utf-8 -*-
"""
Inspection script to verify the completeness of key raw financial columns.
Calculates REAL missing rates from the actual dataset.
"""

import os
import pandas as pd
from src.common.utils import logger, load_csv
from src.common import config

def inspect_raw_columns():
    logger.info("=============================================")
    logger.info("🔍 INSPECTING STRUCTURED RAW DATA COMPLETENESS")
    logger.info("=============================================")

    if not os.path.exists(config.CLEANED_FINANCIALS_FILE):
        logger.error(f"❌ Cleaned financials file not found: {config.CLEANED_FINANCIALS_FILE}")
        return False

    df = load_csv(config.CLEANED_FINANCIALS_FILE)
    if df.empty:
        logger.error("❌ Dataset is empty!")
        return False

    # Target columns to audit
    target_columns = {
        "EBIT": "ebit",
        "interest_expense": "interest_expense",
        "profit_after_tax": "profit_after_tax",
        "total_equity": "total_equity",
        "retained_earnings": "retained_earnings",
        "total_assets": "total_assets"
    }

    # Calculate REAL missing percentages from the actual data
    logger.info("📊 missing các cột RAW (actual measurement):")

    for label, col in target_columns.items():
        if col in df.columns:
            # Count zeros as "present but zero" (not missing)
            # Count NaN/None as truly missing
            missing_count = df[col].isna().sum()
            missing_percent = (missing_count / len(df)) * 100
            status = "✅" if missing_percent < 5.0 else "⚠️"
            logger.info(f"   {status} {label:<18} : {missing_percent:.1f}% missing ({missing_count}/{len(df)})")
        else:
            logger.info(f"   ❌ {label:<18} : COLUMN NOT FOUND")

    logger.info("=============================================")
    return True

def main():
    inspect_raw_columns()

if __name__ == "__main__":
    main()
