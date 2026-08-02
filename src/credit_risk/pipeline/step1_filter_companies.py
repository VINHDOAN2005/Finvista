# -*- coding: utf-8 -*-
"""
Step 1: Get listed companies and filter out financial institutions.
"""

import os
import sys
from typing import List
import pandas as pd

# Reconfigure stdout and stderr to use UTF-8 to prevent UnicodeEncodeError on Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from src.common.utils import logger, load_json, save_json
from src.common import config
from src.credit_risk.helpers.inspect_companies import get_companies_data

def filter_companies() -> List[str]:
    """Filters listed companies to keep only non-financial corporations."""
    logger.info("🎬 STEP 1: Filtering companies list...")
    df = get_companies_data()
    
    initial_count = len(df)
    
    # 1. Filter by Exchange (HOSE, HNX, UPCOM)
    if "exchange" in df.columns:
        df = df[df["exchange"].isin(config.TARGET_EXCHANGES)]
        logger.info(f"   - Filtered by exchange ({', '.join(config.TARGET_EXCHANGES)}): {len(df)}/{initial_count} companies remain.")
        
    # 2. Filter out financial sectors by industry and company name keywords (banks, insurance, securities, funds)
    keywords = [
        "Ngân hàng", "Chứng khoán", "Bảo hiểm", "Quỹ đầu tư", "Quản lý Quỹ",
        "Bank", "Securities", "Insurance", "Investment Fund"
    ]
    
    # Check industry exclusion
    is_excluded_industry = pd.Series(False, index=df.index)
    if "industry" in df.columns:
        is_excluded_industry = df["industry"].isin(config.EXCLUDED_SECTORS)
        
    # Check company name keyword exclusion
    is_excluded_name = pd.Series(False, index=df.index)
    if "company_name" in df.columns:
        name_lower = df["company_name"].str.lower().fillna("")
        for kw in keywords:
            is_excluded_name = is_excluded_name | name_lower.str.contains(kw.lower(), regex=False)
            
    is_excluded = is_excluded_industry | is_excluded_name
    
    filtered_df = df[~is_excluded]
    excluded_df = df[is_excluded]
    
    logger.info(f"   - Excluded financial sectors & companies (by industry or name): {len(excluded_df)} companies removed.")
    logger.info(f"   - Remaining Non-Financial Corporations: {len(filtered_df)} companies.")
    df = filtered_df

    # Clean ticker format (upper case, strip spaces)
    df["ticker"] = df["ticker"].str.strip().str.upper()
    
    # Remove empty or invalid tickers
    df = df[df["ticker"].str.len() == 3]
    
    target_tickers = sorted(df["ticker"].unique().tolist())
    
    # Save the target tickers list
    save_json(target_tickers, config.FILTERED_COMPANIES_FILE)
    logger.info(f"✅ Filtered tickers saved to {config.FILTERED_COMPANIES_FILE}")
    logger.info(f"🎯 Ready to collect data for {len(target_tickers)} companies.")
    
    return target_tickers

def main():
    filter_companies()

if __name__ == "__main__":
    from typing import List
    main()
