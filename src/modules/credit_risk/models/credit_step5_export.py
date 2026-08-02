# -*- coding: utf-8 -*-
"""
Step 5: Export the final training-ready dataset and run quality reports.
Calculates actual missingness from data and saves the structured training file.
"""

import os
import pandas as pd
import numpy as np
from src.core.utils import logger, load_csv, save_csv
from src.core import config

def apply_data_quality_gates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Data Quality Gates (DQ Gates) for filtering NaN, invalid, and outlier inputs prior to model ingestion.
    Filters out:
      1. Rows with missing critical columns (total_assets, total_equity, profit_after_tax).
      2. Rows with excessive missingness (> 40% of feature columns are NaN/Inf).
      3. Extreme outliers by capping features at the 1st and 99th percentiles (Winsorization) to prevent model distortion.
    """
    logger.info("🛡️  Running Data Quality Gates (DQ Gates)...")
    initial_rows = len(df)
    
    # 1. Check critical columns completeness
    critical_cols = ["total_assets", "total_equity", "profit_after_tax"]
    for col in critical_cols:
        if col in df.columns:
            # Replace infinities with NaN first
            df[col] = df[col].replace([np.inf, -np.inf], np.nan)
            # Filter rows where critical column is NaN or total_assets <= 0
            if col == "total_assets":
                df = df[df[col].notna() & (df[col] > 0)]
            else:
                df = df[df[col].notna()]
    logger.info(f"   * Gate 1 (Critical Columns): Retained {len(df)} / {initial_rows} rows")
    
    # 2. Filter rows with high missingness (> 40% NaNs/Infs in numeric columns)
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    feature_cols = [c for c in numeric_cols if c not in ["ticker", "year", "distress_label", "distress_label_next_year"]]
    
    if len(feature_cols) > 0:
        # Check percentage of NaNs or Infs per row
        row_nan_pct = df[feature_cols].replace([np.inf, -np.inf], np.nan).isna().mean(axis=1)
        df = df[row_nan_pct <= 0.40].copy()
    logger.info(f"   * Gate 2 (Row Missingness Limit <= 40%): Retained {len(df)} rows")
    
    # 3. Winsorize extreme outliers at 1% and 99% percentiles for financial feature columns
    outlier_capped = 0
    for col in feature_cols:
        # Replace infinities first
        df[col] = df[col].replace([np.inf, -np.inf], np.nan)
        
        non_nan_series = df[col].dropna()
        if len(non_nan_series) > 0:
            q_low = non_nan_series.quantile(0.01)
            q_high = non_nan_series.quantile(0.99)
            
            # Count how many values are capped
            capped_low = (df[col] < q_low).sum()
            capped_high = (df[col] > q_high).sum()
            outlier_capped += (capped_low + capped_high)
            
            # Apply capping
            df[col] = df[col].clip(lower=q_low, upper=q_high)
            
    logger.info(f"   * Gate 3 (Outlier Capping - Winsorization at 1%/99%): Capped {outlier_capped} extreme values across features")
    return df


def export_final_dataset():
    logger.info("🎬 STEP 5: Exporting final financial distress dataset...")

    if not os.path.exists(config.LABELED_DATA_FILE):
        logger.error(f"❌ Labeled financials data not found: {config.LABELED_DATA_FILE}")
        return False

    df = load_csv(config.LABELED_DATA_FILE)
    if df.empty:
        logger.error("❌ Labeled dataset is empty!")
        return False

    # Apply Data Quality Gates
    df = apply_data_quality_gates(df)

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

    return True

def main():
    export_final_dataset()

if __name__ == "__main__":
    main()
