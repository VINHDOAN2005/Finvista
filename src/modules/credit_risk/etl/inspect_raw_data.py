# -*- coding: utf-8 -*-
"""
Inspection script to verify the completeness of key raw financial columns.
Calculates REAL missing rates from the actual dataset.
"""

import os
import pandas as pd
from src.core.utils import logger, load_csv
from src.core import config

def inspect_raw_columns():
    logger.info("🔍 INSPECTING STRUCTURED RAW DATA COMPLETENESS")

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

    # Calculate REAL missing percentages from the actual data (zero values count as missing/incomplete)
    logger.info("📊 Missing/Incomplete rate of RAW columns (actual measurement):")

    for label, col in target_columns.items():
        if col in df.columns:
            # Count zeroes as missing/incomplete for critical assets/equity/revenue, or NaN
            missing_count = int((df[col] == 0).sum() + df[col].isna().sum())
            missing_percent = (missing_count / len(df)) * 100
            status = "✅" if missing_percent < 5.0 else "⚠️"
            logger.info(f"   {status} {label:<18} : {missing_percent:.1f}% missing/zero ({missing_count}/{len(df)})")
        else:
            logger.info(f"   ❌ {label:<18} : COLUMN NOT FOUND")

    # Load Quality Report summary if it exists
    report_path = os.path.join(config.PROCESSED_DATA_DIR, "data_quality_report.json")
    if os.path.exists(report_path):
        import json
        with open(report_path, "r", encoding="utf-8") as f:
            report = json.load(f)
            violations = report.get("logic_validation", {}).get("violations", [])
            logger.info("📊 Logic Sanity Check Summary:")
            if not violations:
                logger.info("   ✅ All business logic rules passed!")
            else:
                for v in violations:
                    logger.info(f"   ⚠️ {v['check']}: {v['count']} issues found.")

    return True

def main():
    inspect_raw_columns()

if __name__ == "__main__":
    main()
