# -*- coding: utf-8 -*-
"""
Step 5: Export the final training-ready dataset and run quality reports.
Calculates actual missingness from data and saves the structured training file.
"""

import os
import pandas as pd
import numpy as np
from src.common.utils import logger, load_csv, save_csv
from src.common import config

def export_final_dataset():
    logger.info("🎬 STEP 5: Exporting final financial distress dataset...")

    if not os.path.exists(config.LABELED_DATA_FILE):
        logger.error(f"❌ Labeled financials data not found: {config.LABELED_DATA_FILE}")
        return False

    df = load_csv(config.LABELED_DATA_FILE)
    if df.empty:
        logger.error("❌ Labeled dataset is empty!")
        return False

    # 1. Print actual quality check audit (calculated from real data, not hardcoded)
    target_columns_label = {
        "EBIT": "ebit",
        "interest_expense": "interest_expense",
        "profit_after_tax": "profit_after_tax",
        "total_equity": "total_equity",
        "retained_earnings": "retained_earnings",
        "total_assets": "total_assets"
    }

    logger.info("📊 Data Quality Audit (actual measurements):")
    for label, col in target_columns_label.items():
        if col in df.columns:
            nan_count = df[col].isna().sum()
            inf_count = np.isinf(df[col].replace([np.inf, -np.inf], np.nan).astype(float)).sum() if df[col].dtype in [np.float64] else 0
            total_bad = nan_count + inf_count
            rate = (total_bad / len(df)) * 100
            status = "✅" if rate < 5.0 else "⚠️"
            logger.info(f"   {status} {label:<18} : {rate:.1f}% missing/invalid")

    logger.info("=============================================")

    # 2. Impute NaNs/Infs in the actual training set before exporting
    for col in df.columns:
        if df[col].dtype in [np.float64, np.int64, float, int]:
            # Replace infinities
            df[col] = df[col].replace([np.inf, -np.inf], np.nan)
            # Fill NaNs with column median
            if df[col].isna().any():
                median_val = df[col].median()
                df[col] = df[col].fillna(median_val if not pd.isna(median_val) else 0)

    # 3. Create temporal lag label: use year-T features to predict year T+1 distress
    # This is the academically correct setup — no data leakage
    logger.info("⏱️  Creating temporal lag label (distress_label_next_year)...")
    df = df.sort_values(["ticker", "year"]).reset_index(drop=True)
    df["distress_label_next_year"] = (
        df.groupby("ticker")["distress_label"]
        .shift(-1)  # shift UP: row year T gets label of year T+1
    )
    # Drop rows where next-year label is unavailable (last year per ticker)
    valid_mask = df["distress_label_next_year"].notna()
    df_lagged = df[valid_mask].copy()
    df_lagged["distress_label_next_year"] = df_lagged["distress_label_next_year"].astype(int)

    lag_rate = df_lagged["distress_label_next_year"].mean()
    logger.info(f"   📊 Lagged dataset: {len(df_lagged)} records (dropped {len(df) - len(df_lagged)} last-year rows)")
    logger.info(f"   📊 Next-year distress rate: {lag_rate:.2%}")

    # 4. Export both datasets: original (same-year) and lagged (next-year predictive)
    save_csv(df, config.FINAL_DATASET_FILE)
    lagged_file = config.FINAL_DATASET_FILE.replace(".csv", "_lagged.csv")
    save_csv(df_lagged, lagged_file)

    logger.info(f"✅ Saved CSV (same-year):  {config.FINAL_DATASET_FILE}")
    logger.info(f"✅ Saved CSV (lagged T+1): {lagged_file}")

    # Print summary statistics
    logger.info(f"🎉 Dataset Export Completed successfully!")
    logger.info(f"   - Total records (same-year) : {len(df)}")
    logger.info(f"   - Total records (lagged T+1): {len(df_lagged)}")
    logger.info(f"   - Total features            : {len(df.columns) - 6} indicators")
    logger.info(f"   - Distress rate (same-year) : {np.mean(df['distress_label']):.2%}")
    logger.info(f"   - Distress rate (lagged T+1): {lag_rate:.2%}")
    logger.info("=============================================")

    return True

def main():
    export_final_dataset()

if __name__ == "__main__":
    main()
