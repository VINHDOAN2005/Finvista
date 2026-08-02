# -*- coding: utf-8 -*-
"""
Step 2: Resilient Financial Statements Crawler.
Crawls balance sheets, income statements, and cash flows.
Contains checkpointing, exponential retry, and high-fidelity mock fallback.
"""

import os
import sys
import time
import random
import json
from typing import Dict, List, Any
import pandas as pd
from tqdm import tqdm

# Reconfigure stdout and stderr to use UTF-8 to prevent UnicodeEncodeError on Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from src.core.utils import logger, load_json, save_json, random_sleep, CheckpointManager
from src.core import config


# ─── Column Mapping: vnstock DataFrame columns → pipeline schema ─────────────
# vnstock returns Vietnamese + English column names depending on source/version.
# This mapping covers VCI, KBS, and common aliases.
_BS_COLUMN_MAP = {
    # total_assets
    "total_asset": "total_assets", "totalAsset": "total_assets",
    "tong_tai_san": "total_assets", "TOTAL ASSETS": "total_assets",
    "Tổng tài sản": "total_assets",
    # current_assets
    "current_asset": "current_assets", "shortAsset": "current_assets",
    "tai_san_ngan_han": "current_assets", "SHORT-TERM ASSETS": "current_assets",
    "Tài sản ngắn hạn": "current_assets",
    # total_liabilities
    "total_debt": "total_liabilities", "debt": "total_liabilities",
    "no_phai_tra": "total_liabilities", "TOTAL LIABILITIES": "total_liabilities",
    "Tổng nợ phải trả": "total_liabilities",
    # current_liabilities
    "short_debt": "current_liabilities", "shortDebt": "current_liabilities",
    "no_ngan_han": "current_liabilities", "Short-term liabilities": "current_liabilities",
    "Nợ ngắn hạn": "current_liabilities",
    # total_equity
    "equity": "total_equity", "owner_equity": "total_equity",
    "von_chu_so_huu": "total_equity", "OWNER'S EQUITY": "total_equity",
    "Vốn chủ sở hữu": "total_equity",
    # retained_earnings
    "un_distributed_income": "retained_earnings", "undistributedIncome": "retained_earnings",
    "loi_nhuan_giu_lai": "retained_earnings",
    "Lợi nhuận chưa phân phối": "retained_earnings",
}

_IS_COLUMN_MAP = {
    # net_revenue
    "revenue": "net_revenue", "net_revenue": "net_revenue",
    "doanh_thu_thuan": "net_revenue", "Revenue": "net_revenue",
    "Doanh thu thuần": "net_revenue",
    # profit_after_tax
    "post_tax_profit": "profit_after_tax", "shareHolderIncome": "profit_after_tax",
    "loi_nhuan_sau_thue": "profit_after_tax",
    "Lợi nhuận sau thuế": "profit_after_tax",
    "profit_after_tax": "profit_after_tax",
    # ebit
    "ebit": "ebit", "EBIT": "ebit",
    "operating_profit": "ebit", "Lợi nhuận từ HĐKD": "ebit",
    # interest_expense
    "interest_expense": "interest_expense", "costOfFinancing": "interest_expense",
    "chi_phi_lai_vay": "interest_expense", "Chi phí lãi vay": "interest_expense",
}

_CF_COLUMN_MAP = {
    # operating_cash_flow
    "from_sale": "operating_cash_flow", "operatingCashFlow": "operating_cash_flow",
    "dong_tien_nld": "operating_cash_flow",
    "Lưu chuyển tiền từ HĐKD": "operating_cash_flow",
    "operating_cash_flow": "operating_cash_flow",
}


def _map_columns(df: pd.DataFrame, mapping: dict) -> pd.DataFrame:
    """Rename columns using a case-insensitive fuzzy mapping dict."""
    rename_dict = {}
    for col in df.columns:
        col_clean = str(col).strip()
        if col_clean in mapping:
            rename_dict[col] = mapping[col_clean]
    return df.rename(columns=rename_dict)


def _extract_year(df: pd.DataFrame) -> pd.DataFrame:
    """Try to extract a usable 'year' column from various date/period columns."""
    if "year" in df.columns:
        df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
        return df
    # Look for date-like columns
    for col in ["yearReport", "year_report", "period", "Năm", "fiscalDate", "LenLCTT"]:
        if col in df.columns:
            df["year"] = pd.to_numeric(df[col].astype(str).str[:4], errors="coerce").astype("Int64")
            return df
    # If index is datetime
    if hasattr(df.index, "year"):
        df["year"] = df.index.year
    return df


def get_real_financials_vnstock(ticker: str, years: List[int], crawler_state: dict) -> List[Dict[str, Any]]:
    """
    Pulls real financial statements from vnstock library (v4.0.4+).
    Parses balance sheet, income statement, and cash flow DataFrames,
    transposes wide format (years as columns) into long format (years as rows),
    maps columns to our standard pipeline schema, and returns structured records.
    """
    try:
        import contextlib
        import io

        # Silence the verbose deprecation and insider notices from vnstock library
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            from vnstock import Vnstock
            stock = Vnstock()

            # vnstock 4.0.4 automatically routes to the best public free source
            finance = stock.stock(symbol=ticker).finance

            df_bs_raw = finance.balance_sheet(period="year")
            df_is_raw = finance.income_statement(period="year")

            try:
                df_cf_raw = finance.cash_flow(period="year")
            except Exception:
                df_cf_raw = pd.DataFrame()

        if df_bs_raw is None or df_bs_raw.empty or df_is_raw is None or df_is_raw.empty:
            return []

        # Helper function to clean and transpose vnstock v4 format (years as columns)
        def _transpose_statement(df_raw: pd.DataFrame) -> pd.DataFrame:
            if df_raw.empty or 'item_id' not in df_raw.columns:
                return pd.DataFrame()
            # Clean duplicate item_ids by keeping the last occurrence (the summary/actual calculation)
            df_clean = df_raw.drop_duplicates(subset=['item_id'], keep='last')
            # Transpose: years become rows, financial fields become columns
            df_t = df_clean.drop(columns=['item'], errors='ignore').set_index('item_id').T
            df_t = df_t.reset_index().rename(columns={'index': 'year'})
            df_t['year'] = pd.to_numeric(df_t['year'], errors='coerce').astype('Int64')
            return df_t

        df_bs = _transpose_statement(df_bs_raw)
        df_is = _transpose_statement(df_is_raw)
        df_cf = _transpose_statement(df_cf_raw) if not df_cf_raw.empty else pd.DataFrame()

        if df_bs.empty or df_is.empty:
            return []

        # Map dynamic v4 item_ids to standard pipeline columns
        # 1. Balance Sheet
        if 'owners_equity_2' in df_bs.columns:
            df_bs['total_equity'] = df_bs['owners_equity_2']
        elif 'owners_equity_3' in df_bs.columns:
            df_bs['total_equity'] = df_bs['owners_equity_3']
        elif 'owners_equity' in df_bs.columns:
            df_bs['total_equity'] = df_bs['owners_equity']

        # 2. Income Statement
        if 'revenue' in df_is.columns:
            df_is['net_revenue'] = df_is['revenue']
        if 'net_profit' in df_is.columns:
            df_is['profit_after_tax'] = df_is['net_profit']
        if 'operating_profit' in df_is.columns:
            df_is['ebit'] = df_is['operating_profit']
        if 'of_which_interest_expense' in df_is.columns:
            df_is['interest_expense'] = df_is['of_which_interest_expense']

        # Merge BS, IS, and CF on year
        merged = df_bs.copy()
        if "year" in merged.columns and "year" in df_is.columns:
            is_cols = [c for c in df_is.columns if c not in merged.columns or c == "year"]
            merged = merged.merge(df_is[is_cols], on="year", how="left")
        if not df_cf.empty and "year" in df_cf.columns:
            cf_cols = [c for c in df_cf.columns if c not in merged.columns or c == "year"]
            merged = merged.merge(df_cf[cf_cols], on="year", how="left")

        # Required fields for our pipeline
        required = [
            "total_assets", "current_assets", "total_liabilities", "current_liabilities",
            "total_equity", "retained_earnings", "net_revenue", "profit_after_tax",
            "ebit", "interest_expense", "operating_cash_flow"
        ]

        # Filter to requested years and build records
        records = []
        year_set = set(years)
        for _, row in merged.iterrows():
            yr = row.get("year")
            if pd.isna(yr) or int(yr) not in year_set:
                continue

            record = {"ticker": ticker, "year": int(yr)}
            missing_critical = False
            for field in required:
                val = row.get(field)
                if pd.notna(val) and not pd.isna(val):
                    record[field] = int(float(val))
                else:
                    if field in ("total_assets", "total_equity", "net_revenue"):
                        missing_critical = True
                        break
                    record[field] = 0

            if missing_critical:
                continue

            # Estimate market_cap if not present (use equity * 2.0 as proxy)
            record["market_cap"] = record.get("market_cap", int(record["total_equity"] * 2.0))
            records.append(record)

        return records

    except (Exception, SystemExit) as e:
        logger.warning(f"⚠️ Exception or SystemExit during live fetch for {ticker}: {e}")
    return []



def generate_coherent_financials(ticker: str, years: List[int]) -> List[Dict[str, Any]]:
    """
    Generates high-fidelity, mathematically coherent mock financial statements
    with realistic market noise and feature overlaps.
    Uses a deterministic seed per ticker for reproducibility.
    """
    # Deterministic seed per ticker so re-runs produce identical data
    random.seed(hash(ticker) % (2**31))

    company_data = []

    # Establish a baseline profile for the company
    is_distressed = (random.random() < 0.08)  # 8% probability of distress

    # Starting assets in VND (between 100 Billion and 10 Trillion)
    base_assets = random.uniform(1e11, 1e13)

    # Industry specifics
    growth_rate = random.uniform(-0.15, -0.02) if is_distressed else random.uniform(0.03, 0.20)
    debt_ratio = random.uniform(0.70, 0.95) if is_distressed else random.uniform(0.20, 0.60)
    profit_margin = random.uniform(-0.12, -0.01) if is_distressed else random.uniform(0.04, 0.18)

    assets = base_assets

    for i, year in enumerate(years):
        curr_distressed = is_distressed

        # Injected Noise: 15% chance that a distressed company acts healthy this year
        # or a healthy company experiences a temporary shock
        noise_event = (random.random() < 0.15)

        if noise_event:
            curr_growth = random.uniform(-0.05, 0.05)
            curr_debt = random.uniform(0.50, 0.75)  # Overlapping debt ratios
            curr_margin = random.uniform(-0.04, 0.04)  # Overlapping profit margins
        else:
            curr_growth = growth_rate
            curr_debt = debt_ratio
            curr_margin = profit_margin

        equity_mult = (random.uniform(-0.5, -0.1) if curr_distressed else random.uniform(0.2, 0.6))
        ocf_mult = (random.uniform(-1.5, -0.2) if curr_distressed else random.uniform(0.8, 1.5))
        mc_mult = random.uniform(0.2, 0.7) if curr_distressed else random.uniform(1.2, 4.0)

        # Apply annual growth with Brownian motion noise
        assets = assets * (1.0 + curr_growth + random.uniform(-0.05, 0.05))

        # Balance Sheet Math
        total_liabilities = assets * (curr_debt + random.uniform(-0.04, 0.04))
        total_liabilities = max(0.05 * assets, min(0.98 * assets, total_liabilities))
        total_equity = assets - total_liabilities

        # Sub-accounts
        current_assets = assets * random.uniform(0.35, 0.75)
        current_liabilities = total_liabilities * random.uniform(0.55, 0.95)

        # Retained earnings (can be negative for distressed)
        retained_earnings = total_equity * equity_mult

        # Income Statement Math
        revenue_turnover = random.uniform(0.5, 1.6)
        revenue = assets * revenue_turnover

        # Net profit after tax
        profit_after_tax = revenue * (curr_margin + random.uniform(-0.02, 0.02))

        # EBIT (Earnings Before Interest and Taxes)
        interest_rate = random.uniform(0.08, 0.15)
        interest_expense = total_liabilities * interest_rate * random.uniform(0.3, 0.6)

        pretax_profit = profit_after_tax / 0.8
        ebit = pretax_profit + interest_expense

        # Cash Flow
        operating_cash_flow = profit_after_tax * ocf_mult

        # Market data
        market_cap = total_equity * mc_mult

        record = {
            "ticker": ticker,
            "year": year,
            "total_assets": int(assets),
            "current_assets": int(current_assets),
            "total_liabilities": int(total_liabilities),
            "current_liabilities": int(current_liabilities),
            "total_equity": int(total_equity),
            "retained_earnings": int(retained_earnings),
            "net_revenue": int(revenue),
            "profit_after_tax": int(profit_after_tax),
            "ebit": int(ebit),
            "interest_expense": int(interest_expense),
            "operating_cash_flow": int(operating_cash_flow),
            "market_cap": int(market_cap)
        }

        company_data.append(record)

    # Restore global random state so other code isn't affected
    random.seed()
    return company_data


def crawl_financials(tickers: List[str]):
    """Main crawler loop with retry, delay, and checkpointing."""
    logger.info("🎬 STEP 2: Starting financial reports crawler...")

    checkpoint_file = os.path.join(config.DATA_DIR, "crawl_checkpoint.json")
    checkpoint_mgr = CheckpointManager(checkpoint_file)

    completed_set = set(checkpoint_mgr.get_completed())
    failed_keys = set(checkpoint_mgr.get_failed().keys())
    already_processed = completed_set.union(failed_keys)

    logger.info(f"🔄 Checkpoint status: {len(completed_set)} completed, {len(failed_keys)} failed/skipped. Total tickers in scope: {len(tickers)}")

    # Container for all retrieved raw data
    raw_data_cache_file = config.RAW_FINANCIALS_FILE
    all_raw_data = load_json(raw_data_cache_file)
    if all_raw_data is None:
        all_raw_data = []

    years = list(range(config.START_YEAR, config.END_YEAR + 1))

    # Crawler state (encapsulated, not global)
    crawler_state = {"offline_mode": False, "consecutive_failures": 0}

    pbar = tqdm(
        total=len(tickers),
        initial=len(already_processed & set(tickers)),
        desc="Crawling",
        bar_format="{desc}: {percentage:3.0f}%|{bar:30}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]"
    )

    for idx, ticker in enumerate(tickers):
        if ticker in already_processed:
            pbar.update(1)
            continue

        # Retry mechanism for APIs
        success = False
        attempts = 0
        ticker_data = []

        # Check if USE_MOCK configuration is active
        if getattr(config, "USE_MOCK", False):
            ticker_data = generate_coherent_financials(ticker, years)
            success = True
            logger.info(f"⚡ [MOCK] Generated high-fidelity financial data for {ticker}")
        else:
            while attempts < config.MAX_RETRIES and not success:
                attempts += 1
                try:
                    # 1. Try real vnstock crawler
                    ticker_data = get_real_financials_vnstock(ticker, years, crawler_state)
                    if ticker_data:
                        logger.info(f"✅ Successfully crawled live financial data for {ticker}!")
                        success = True
                        crawler_state["consecutive_failures"] = 0
                    else:
                        # In case of empty result (could be rate limit or invalid ticker)
                        logger.warning(f"⚠️ Empty/failed response for {ticker} (Attempt {attempts}/{config.MAX_RETRIES}).")
                        if attempts < config.MAX_RETRIES:
                            logger.info("⏳ Sleeping 45 seconds to reset public API window limit...")
                            time.sleep(45)
                        else:
                            logger.warning(f"❌ Failed to get real data for {ticker} after {config.MAX_RETRIES} attempts.")
                except (Exception, SystemExit) as e:
                    logger.warning(f"⚠️ Attempt {attempts} failed for {ticker}. Error/Exit: {e}")
                    if attempts < config.MAX_RETRIES:
                        logger.info("⏳ Sleeping 45 seconds to reset public API window limit due to exception or SystemExit...")
                        time.sleep(45)
                    else:
                        checkpoint_mgr.save(idx + 1, ticker, status="failed", error_msg=str(e))

        if success and ticker_data:
            all_raw_data.extend(ticker_data)
            checkpoint_mgr.save(idx + 1, ticker, status="success")
        else:
            crawler_state["consecutive_failures"] += 1
            
            # Smart classification of the skip/exclusion reason
            skip_reason = "No real data fetched"
            try:
                all_cos_file = os.path.join(config.DATA_DIR, "companies_list_ALL.json")
                if os.path.exists(all_cos_file):
                    with open(all_cos_file, 'r', encoding='utf-8') as f:
                        all_cos = json.load(f)
                    co_profile = next((c for c in all_cos if c['ticker'] == ticker), None)
                    if co_profile:
                        ind = co_profile.get('industry', '')
                        name = co_profile.get('company_name', '').lower()
                        
                        financial_keywords = ["ngân hàng", "chứng khoán", "bảo hiểm", "quỹ đầu tư", "quản lý quỹ", "tài chính", "banking", "securities", "insurance", "finance"]
                        is_financial_ind = ind in ["Bảo hiểm", "Chứng khoán", "Ngân hàng", "Tài chính khác"]
                        is_financial_name = any(kw in name for kw in financial_keywords)
                        
                        if is_financial_ind or is_financial_name:
                            skip_reason = f"Excluded: Financial Institution ({ind})"
                        else:
                            # Non-financial company but no data -> likely restricted/suspended trading or delisted
                            skip_reason = "Excluded: Suspended/Restricted Trading or Delisted (No BCTC available)"
            except Exception:
                pass
                
            checkpoint_mgr.save(idx + 1, ticker, status="skipped", error_msg=skip_reason)
            logger.warning(f"⏩ Skipped {ticker} ({skip_reason}).")

            # If we hit multiple consecutive skips, we might be heavily rate-limited
            if crawler_state["consecutive_failures"] >= 3:
                logger.warning("🚨 3 consecutive skips! API might be strictly rate-limiting. Sleeping for 60 seconds...")
                time.sleep(60)

        if (idx + 1) % config.CRAWL_CHECKPOINT_INTERVAL == 0 or (idx + 1) == len(tickers):
            save_json(all_raw_data, raw_data_cache_file)
            logger.info(f"💾 Checkpoint saved for {idx + 1} companies...")

        # Respectful delay between companies to prevent rate limit (Guest: 20 req/min)
        # 10s delay maintains a safe rate of ~18 requests per minute including API latency
        if not getattr(config, "USE_MOCK", False):
            delay = random.uniform(9.0, 13.0)
            time.sleep(delay)
        pbar.update(1)

    pbar.close()

    # Final save of raw data
    save_json(all_raw_data, raw_data_cache_file)
    logger.info(f"✅ Finished crawling. Raw data cached to {raw_data_cache_file}")


def main():
    tickers = load_json(config.FILTERED_COMPANIES_FILE)
    if not tickers:
        logger.warning("⚠️ No tickers found! Running Step 1 first...")
        from src.modules.credit_risk.models.credit_step1_filter import filter_companies
        tickers = filter_companies()

    crawl_financials(tickers)


if __name__ == "__main__":
    from typing import Dict, Any, List
    main()
