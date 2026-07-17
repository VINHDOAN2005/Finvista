# -*- coding: utf-8 -*-
"""
Inspection script to explore listed companies, sector distributions, and statistics.
Uses vnstock v4.0.4 API: Listing.symbols_by_exchange() + Listing.symbols_by_industries()
"""

import os
import pandas as pd
from src.common.utils import logger, load_json, save_json
from src.common import config


def get_companies_data() -> pd.DataFrame:
    """Fetches company listings from vnstock v4 API or loads from local cache.
    
    Returns a DataFrame with columns: ticker, company_name, exchange, industry.
    Raises RuntimeError if API fails and no cache is available.
    """
    # Determine cache file based on group
    group_name = config.TICKER_GROUP if config.TICKER_GROUP else "ALL"
    cache_file = os.path.join(config.DATA_DIR, f"companies_list_{group_name}.json")

    # 1. Try local cache first
    if os.path.exists(cache_file):
        logger.info(f"📂 Loading companies list from cache: {cache_file}")
        data = load_json(cache_file)
        if data:
            return pd.DataFrame(data)

    # 2. Fetch from vnstock v4 API (no mock fallback)
    logger.info("🌐 Fetching real-time company list from vnstock v4...")
    from vnstock import Listing
    listing = Listing()

    # 2a. Get all stock tickers + exchange (filter type='stock' only)
    df_exchange = listing.symbols_by_exchange(show=False)
    df_stocks = df_exchange[df_exchange["type"] == "stock"][["symbol", "organ_name", "exchange"]].copy()
    df_stocks.rename(columns={"symbol": "ticker", "organ_name": "company_name"}, inplace=True)
    logger.info(f"   ✅ symbols_by_exchange: {len(df_stocks)} stock tickers fetched.")

    # Apply Ticker Group filter if applicable
    if config.TICKER_GROUP and config.TICKER_GROUP.upper() != "ALL":
        grp = config.TICKER_GROUP.upper()
        logger.info(f"🔍 Filtering to group: {grp}")
        try:
            group_series = listing.symbols_by_group(grp)
            group_tickers = set(group_series.tolist())
            df_stocks = df_stocks[df_stocks["ticker"].isin(group_tickers)].copy()
            logger.info(f"   ✅ Filtered to {len(df_stocks)} tickers in {grp}.")
        except Exception as ex:
            logger.warning(f"⚠️ Could not fetch group {grp}: {ex}. Using all tickers.")

    # 2b. Get industry classification and merge
    df_industry = listing.symbols_by_industries(show=False)[["symbol", "industry_name"]].copy()
    df_industry.rename(columns={"symbol": "ticker", "industry_name": "industry"}, inplace=True)
    logger.info(f"   ✅ symbols_by_industries: {len(df_industry)} tickers with industry data.")

    # 2c. Left-join so all tickers are kept even if industry is missing
    df = df_stocks.merge(df_industry, on="ticker", how="left")
    df["industry"] = df["industry"].fillna("Khác")

    logger.info(f"   ✅ Final merged company list: {len(df)} tickers.")

    # 3. Cache result locally
    records = df.to_dict(orient="records")
    save_json(records, cache_file)
    logger.info(f"💾 Company list cached to: {cache_file}")
    return df


def main():
    logger.info("=============================================")
    logger.info("📊 INSPECTING LISTED COMPANIES DISTRIBUTION")
    logger.info("=============================================")

    df = get_companies_data()

    # 1. General Summary
    logger.info(f"📈 Total listed companies found: {len(df)}")

    # 2. Exchange Breakdown
    if "exchange" in df.columns:
        logger.info("📍 Breakdown by Exchange:")
        for exchange, count in df["exchange"].value_counts().items():
            logger.info(f"   - {exchange:<8}: {count:>4} companies")

    # 3. Industry Breakdown
    if "industry" in df.columns:
        logger.info("🏭 Top 15 Sectors / Industries:")
        for industry, count in df["industry"].value_counts().head(15).items():
            logger.info(f"   - {industry:<30}: {count:>4} companies")

    # 4. Check for Financial Sectors to filter
    if "industry" in df.columns:
        financial_mask = df["industry"].isin(config.EXCLUDED_SECTORS)
        financial_count = financial_mask.sum()
        logger.info(f"🏦 Total Financial Institutions found: {financial_count} ({financial_count/len(df):.2%})")
        logger.info(f"🏢 Total Non-Financial Corporations: {len(df) - financial_count} (target for distress model)")

    logger.info("=============================================")


if __name__ == "__main__":
    main()
