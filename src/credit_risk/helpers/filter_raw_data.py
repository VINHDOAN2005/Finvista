# -*- coding: utf-8 -*-
"""
Intermediate processing step: Convert raw financial JSON to structured CSV
and clean columns, handle data issues.
"""

import os
import pandas as pd
import numpy as np
from src.common.utils import logger, load_json, save_csv
from src.common import config

def filter_and_clean_raw_data():
    logger.info("🎬 Filtering and cleaning raw financial data...")

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

    # Standardize column naming variations (handles both vnstock real and simulator output)
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

    # Numeric coercion: ensure all financial columns are numeric
    numeric_cols = [
        "total_assets", "current_assets", "total_liabilities", "current_liabilities",
        "total_equity", "retained_earnings", "net_revenue", "profit_after_tax",
        "ebit", "interest_expense", "operating_cash_flow", "market_cap"
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(np.int64)

    # Remove duplicates
    df.drop_duplicates(subset=["ticker", "year"], inplace=True)

    # Save structured intermediate CSV
    save_csv(df, config.CLEANED_FINANCIALS_FILE)
    logger.info(f"✅ Cleaned financial data saved to {config.CLEANED_FINANCIALS_FILE}")
    return True

def main():
    filter_and_clean_raw_data()

if __name__ == "__main__":
    main()
