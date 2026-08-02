# -*- coding: utf-8 -*-
"""
Intermediate processing step: Convert raw financial JSON to structured CSV,
clean columns, handle data issues, and perform comprehensive Data Quality Checks.
"""

import os
import json
import pandas as pd
import numpy as np
from src.core.utils import logger, load_json, save_csv, save_json
from src.core import config

def filter_and_clean_raw_data():
    logger.info("🎬 Step 2.5: Filtering, cleaning raw financial data, and running Data Quality checks...")

    # Load raw financials from step 2
    if not os.path.exists(config.RAW_FINANCIALS_FILE):
        logger.error(f"❌ Raw financials file not found: {config.RAW_FINANCIALS_FILE}")
        return False

    raw_data = load_json(config.RAW_FINANCIALS_FILE)
    if not raw_data:
        logger.error("❌ Raw financials dataset is empty!")
        return False

    df = pd.DataFrame(raw_data)
    logger.info(f"📊 Raw dataset loaded: {len(df)} company-year records.")

    # 1. Standardize column naming variations
    column_mapping = {
        "Total Assets": "total_assets",
        "tong_tai_san": "total_assets",
        "Current Assets": "current_assets",
        "tai_san_ngan_han": "current_assets",
        "Total Liabilities": "total_liabilities",
        "no_phai_tra": "total_liabilities",
        "Current Liabilities": "current_liabilities",
        "no_ngan_han": "current_liabilities",
        "Total Equity": "total_equity",
        "von_chu_so_huu": "total_equity",
        "Retained Earnings": "retained_earnings",
        "loi_nhuan_giu_lai": "retained_earnings",
        "Net Revenue": "net_revenue",
        "doanh_thu_thuan": "net_revenue",
        "Profit After Tax": "profit_after_tax",
        "loi_nhuan_sau_thue": "profit_after_tax",
        "EBIT": "ebit",
        "Interest Expense": "interest_expense",
        "chi_phi_lai_vay": "interest_expense",
        "Operating Cash Flow": "operating_cash_flow",
        "dong_tien_nld": "operating_cash_flow",
        "Market Cap": "market_cap",
        "von_hoa": "market_cap"
    }

    df.rename(columns=column_mapping, inplace=True)

    # 2. Schema Check & Validation
    required_cols = [
        "total_assets", "current_assets", "total_liabilities", "current_liabilities",
        "total_equity", "retained_earnings", "net_revenue", "profit_after_tax",
        "ebit", "interest_expense", "operating_cash_flow", "market_cap"
    ]
    
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        logger.warning(f"⚠️ Missing columns in raw data schema: {missing_cols}. They will be initialized to 0.")
        for col in missing_cols:
            df[col] = 0

    # 3. Numeric Coercion & Data Type Quality Check
    coerced_errors = 0
    for col in required_cols:
        before_nulls = int(df[col].isna().sum())
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(np.int64)
        after_nulls = int(df[col].isna().sum())
        coerced_errors += int(before_nulls - after_nulls)

    # 4. Remove Duplicates
    initial_len = len(df)
    df.drop_duplicates(subset=["ticker", "year"], inplace=True)
    duplicate_count = int(initial_len - len(df))
    if duplicate_count > 0:
        logger.info(f"   🧹 Removed {duplicate_count} duplicate ticker-year records.")

    # 5. Data Quality Audit & Logic Checks (Quality Gates)
    logger.info("🛡️ Running Pipeline Quality Gates...")
    
    total_records = int(len(df))
    
    # 5a. Completeness Audit (Check for zero/missing values in critical columns)
    completeness_report = {}
    critical_columns = ["total_assets", "total_equity", "net_revenue", "profit_after_tax"]
    
    for col in critical_columns:
        # For business logic, a zero total_assets or total_equity is considered missing/invalid
        zero_or_nan = (df[col] == 0) | df[col].isna()
        missing_count = int(zero_or_nan.sum())
        missing_rate = float(missing_count / total_records) if total_records > 0 else 0.0
        
        status = "PASSED" if missing_rate < 0.05 else "WARNING"
        completeness_report[col] = {
            "missing_count": missing_count,
            "missing_rate": missing_rate,
            "status": status
        }
        
        icon = "✅" if status == "PASSED" else "⚠️"
        logger.info(f"   {icon} Completeness check - {col:<18} : {missing_rate:.2%} missing/zero ({missing_count}/{total_records})")

    # 5b. Business Logic Validation (Sanity Checks)
    logic_violations = []
    
    # Check 1: Negative assets (impossible in accounting)
    neg_assets = df[df["total_assets"] < 0]
    if not neg_assets.empty:
        msg = f"Found {len(neg_assets)} records with negative total assets!"
        logic_violations.append({"check": "negative_total_assets", "count": int(len(neg_assets)), "details": [str(x) for x in neg_assets["ticker"].unique()]})
        logger.warning(f"   ❌ Logic violation: {msg}")
        # Fix: force to positive or zero
        df.loc[df["total_assets"] < 0, "total_assets"] = 0
    else:
        logger.info("   ✅ Logic check - negative_total_assets : PASSED")

    # Check 2: Balance sheet equation balance: Total Assets = Total Liabilities + Total Equity
    # We allow a small tolerance (e.g. 5%) due to rounding in financial reports
    bs_diff = (df["total_assets"] - (df["total_liabilities"] + df["total_equity"])).abs()
    bs_ratio_diff = np.where(df["total_assets"] == 0, 0.0, bs_diff / df["total_assets"])
    imbalance_records = df[bs_ratio_diff > 0.05]
    
    if not imbalance_records.empty:
        msg = f"Found {len(imbalance_records)} records where Assets != Liabilities + Equity (tolerance > 5%)"
        logic_violations.append({"check": "balance_sheet_imbalance", "count": int(len(imbalance_records)), "details": [str(x) for x in imbalance_records["ticker"].unique()[:10]]})
        logger.warning(f"   ⚠️ Logic warning: {msg}")
    else:
        logger.info("   ✅ Logic check - balance_sheet_imbalance : PASSED (within 5% tolerance)")

    # Check 3: Current assets vs Total assets sanity check (Current Assets should be <= Total Assets)
    assets_imbalance = df[df["current_assets"] > df["total_assets"]]
    if not assets_imbalance.empty:
        msg = f"Found {len(assets_imbalance)} records where current_assets > total_assets!"
        logic_violations.append({"check": "current_assets_gt_total_assets", "count": int(len(assets_imbalance)), "details": [str(x) for x in assets_imbalance["ticker"].unique()]})
        logger.warning(f"   ❌ Logic violation: {msg}")
        # Fix: cap current assets at total assets
        df.loc[df["current_assets"] > df["total_assets"], "current_assets"] = df["total_assets"]
    else:
        logger.info("   ✅ Logic check - current_assets_limit : PASSED")

    # Check 4: Outliers - debt_ratio = liabilities / assets (should be < 3.0 unless extreme distress)
    extreme_debt = df[df["total_liabilities"] > df["total_assets"] * 3]
    if not extreme_debt.empty:
        msg = f"Found {len(extreme_debt)} records with extreme debt ratio (Liabilities > 3x Assets)"
        logic_violations.append({"check": "extreme_debt_ratio", "count": int(len(extreme_debt)), "details": [str(x) for x in extreme_debt["ticker"].unique()]})
        logger.warning(f"   ⚠️ Logic warning: {msg}")
    else:
        logger.info("   ✅ Logic check - extreme_debt_ratio : PASSED")

    # 6. Save Data Quality Report
    quality_report = {
        "dataset_summary": {
            "total_records": int(total_records),
            "duplicate_records_removed": int(duplicate_count),
            "numeric_coercion_errors": int(coerced_errors)
        },
        "completeness_audit": completeness_report,
        "logic_validation": {
            "passed": len(logic_violations) == 0,
            "violations": logic_violations
        }
    }
    
    report_path = os.path.join(config.PROCESSED_DATA_DIR, "data_quality_report.json")
    save_json(quality_report, report_path)
    logger.info(f"💾 Data Quality audit report saved to {report_path}")

    # 7. Save structured intermediate CSV
    save_csv(df, config.CLEANED_FINANCIALS_FILE)
    logger.info(f"✅ Cleaned financial data saved to {config.CLEANED_FINANCIALS_FILE}")
    return True

def main():
    filter_and_clean_raw_data()

if __name__ == "__main__":
    main()
