# -*- coding: utf-8 -*-
"""
Step 3: Compute Financial Ratios and Features (Refined).
Calculates industry-standard metrics like ROAA and ROAE,
plus Industry-Adjusted features for relative performance analysis.
"""

import os
import json
import pandas as pd
import numpy as np
from src.core.utils import logger, load_csv, save_csv
from src.core import config

def compute_financial_features():
    logger.info("🎬 STEP 3: Computing financial ratios and features (Research Standard)...")
    
    if not os.path.exists(config.CLEANED_FINANCIALS_FILE):
        logger.error(f"❌ Structured financial data not found: {config.CLEANED_FINANCIALS_FILE}")
        return False
        
    df = load_csv(config.CLEANED_FINANCIALS_FILE)
    if df.empty:
        logger.error("❌ Cleaned dataset is empty!")
        return False
        
    # Sort by ticker and year to compute lag/growth variables
    df.sort_values(by=["ticker", "year"], inplace=True)
    
    # --- Load Industry Mapping ---
    companies_json = os.path.join(config.DATA_DIR, "companies_list_ALL.json")
    industry_map = {}
    if os.path.exists(companies_json):
        try:
            with open(companies_json, 'r', encoding='utf-8') as f:
                companies_list = json.load(f)
                industry_map = {c['ticker']: c.get('industry', 'Other') for c in companies_list}
        except Exception as e:
            logger.warning(f"⚠️ Could not load industry mapping: {e}")
    
    df['industry'] = df['ticker'].map(industry_map).fillna('Other')
    
    logger.info("⚙️ Calculating ROAA, ROAE, and Industry-Adjusted metrics...")
    
    # 1. Advanced Profitability: ROAA & ROAE (Research Standard)
    # ROAA = PAT / Average Total Assets
    # ROAE = PAT / Average Total Equity
    df["roaa"] = 0.0
    df["roae"] = 0.0
    
    for ticker, group in df.groupby("ticker"):
        if len(group) >= 2:
            # Average Assets = (Assets_T + Assets_T-1) / 2
            avg_assets = (group["total_assets"] + group["total_assets"].shift(1)) / 2
            avg_equity = (group["total_equity"] + group["total_equity"].shift(1)) / 2
            
            df.loc[group.index, "roaa"] = np.where(avg_assets > 0, group["profit_after_tax"] / avg_assets, group["profit_after_tax"] / group["total_assets"])
            df.loc[group.index, "roae"] = np.where(avg_equity > 0, group["profit_after_tax"] / avg_equity, group["profit_after_tax"] / group["total_equity"])
        else:
            # Fallback for single record
            df.loc[group.index, "roaa"] = np.where(group["total_assets"] > 0, group["profit_after_tax"] / group["total_assets"], 0.0)
            df.loc[group.index, "roae"] = np.where(group["total_equity"] > 0, group["profit_after_tax"] / group["total_equity"], 0.0)

    # 2. Industry-Adjusted Features (Relative Performance)
    # Standardizing metrics by industry-year groups
    logger.info("⚙️ Calculating Industry-Adjusted Benchmarks...")
    # Pre-calculate debt_ratio as it's needed for adjustments
    df["debt_ratio"] = np.where(df["total_assets"] == 0, 0.0, df["total_liabilities"] / df["total_assets"])
    
    for year in df['year'].unique():
        year_mask = df['year'] == year
        for metric in ['roaa', 'roae', 'debt_ratio']:
            if metric in df.columns:
                # Calculate industry mean for that specific year
                ind_mean = df[year_mask].groupby('industry')[metric].transform('mean')
                df.loc[year_mask, f"industry_adjusted_{metric}"] = df.loc[year_mask, metric] - ind_mean
                # Also add industry rank (percentile)
                df.loc[year_mask, f"industry_{metric}_percentile"] = df[year_mask].groupby('industry')[metric].rank(pct=True)

    # 3. Liquidity Indicators
    df["current_ratio"] = np.where(df["current_liabilities"] == 0, 9999.0, df["current_assets"] / df["current_liabilities"])
    df["working_capital"] = df["current_assets"] - df["current_liabilities"]
    df["working_capital_to_assets"] = np.where(df["total_assets"] == 0, 0.0, df["working_capital"] / df["total_assets"])
    df["ocf_to_current_liabilities"] = np.where(df["current_liabilities"] == 0, 0.0, df["operating_cash_flow"] / df["current_liabilities"])
    
    # Cash ratio: Tiền & tương đương / Nợ ngắn hạn
    cash_col = "cash_and_equivalents" if "cash_and_equivalents" in df.columns else "current_assets"
    df["cash_ratio"] = np.where(df["current_liabilities"] == 0, 9999.0, df[cash_col] / df["current_liabilities"])
    # OCF-to-total-debt (dòng tiền so với toàn bộ nợ)
    df["ocf_to_total_debt"] = np.where(df["total_liabilities"] == 0, 0.0, df["operating_cash_flow"] / df["total_liabilities"])
    # Cash flow interest coverage (CFO interest coverage)
    df["cfo_interest_coverage"] = np.where(df["interest_expense"] == 0, 9999.0, (df["operating_cash_flow"] + df["interest_expense"]) / df["interest_expense"])
    
    # 4. Profitability Indicators
    df["roa"] = np.where(df["total_assets"] == 0, 0.0, df["profit_after_tax"] / df["total_assets"])
    df["roe"] = np.where(df["total_equity"] == 0, 0.0, df["profit_after_tax"] / df["total_equity"])
    df["operating_margin"] = np.where(df["net_revenue"] == 0, 0.0, df["ebit"] / df["net_revenue"])
    df["ebit_to_assets"] = np.where(df["total_assets"] == 0, 0.0, df["ebit"] / df["total_assets"])
    # Earnings quality: CFO / Net Profit After Tax
    df["ocf_to_pat"] = np.where(df["profit_after_tax"] == 0, 0.0, df["operating_cash_flow"] / df["profit_after_tax"])
    
    # 5. Leverage Indicators
    df["equity_multiplier"] = np.where(df["total_equity"] == 0, 9999.0, df["total_assets"] / df["total_equity"])
    df["ebit_to_interest"] = np.where(df["interest_expense"] == 0, 9999.0, df["ebit"] / df["interest_expense"])
    df["icr"] = df["ebit_to_interest"]
    df["debt_to_equity"] = np.where(df["total_equity"] == 0, 9999.0, df["total_liabilities"] / df["total_equity"])
    
    # 6. Size and Growth Indicators
    df["company_size"] = np.where(df["total_assets"] <= 0, 0.0, np.log(df["total_assets"]))
    df["revenue_growth"] = 0.0
    df["assets_growth"] = 0.0
    
    for ticker, group in df.groupby("ticker"):
        if len(group) > 1:
            rev_pct = group["net_revenue"].pct_change().fillna(0.0)
            assets_pct = group["total_assets"].pct_change().fillna(0.0)
            df.loc[group.index, "revenue_growth"] = rev_pct
            df.loc[group.index, "assets_growth"] = assets_pct
            
    # 7. Altman Z''-Score Components
    df["altman_x1"] = df["working_capital_to_assets"]
    df["altman_x2"] = np.where(df["total_assets"] == 0, 0.0, df["retained_earnings"] / df["total_assets"])
    df["altman_x3"] = df["ebit_to_assets"]
    df["altman_x4"] = np.where(df["total_liabilities"] == 0, 9999.0, df["market_cap"] / df["total_liabilities"])

    df["altman_z_score"] = (6.56 * df["altman_x1"] + 
                            3.26 * df["altman_x2"] + 
                            6.72 * df["altman_x3"] + 
                            1.05 * df["altman_x4"])

    # --- FINVISTA 2.0: MERTON MODEL & MACRO SENSITIVITY ---
    logger.info("⚙️ Finvista 2.0: Adding Merton Structural Risk & Macro Sensitivity...")

    # 8. Merton Distance to Default (Structural Risk Approximation)
    # Asset_Value (V) approx Market_Cap + Total_Liabilities
    # Asset_Vol (sigma_V) approx (Market_Cap / V) * Equity_Vol
    # DD = (ln(V/D) + (r - sigma_V^2/2)T) / (sigma_V * sqrt(T))

    # Fetch Equity Volatility (use 120-day annualized if available, fallback to default 0.3)
    try:
        from src.modules.credit_risk.systemic.network_builder import calculate_stock_volatility_proxies
        all_tickers = df["ticker"].unique().tolist()
        vol_map = calculate_stock_volatility_proxies(all_tickers)
        df["equity_vol"] = df["ticker"].map(vol_map).fillna(0.3)
    except Exception as e:
        logger.warning(f"⚠️ Failed to fetch equity vol for Merton model: {e}")
        df["equity_vol"] = 0.3

    r = 0.035 # Proxy Risk-free rate (Vietnam 1Y Gov Yield approx)
    T = 1.0   # 1-year horizon

    v_asset = df["market_cap"] + df["total_liabilities"]
    d_debt = df["total_liabilities"]

    # Avoid log(0)
    v_safe = np.where(v_asset <= 0, 1.0, v_asset)
    d_safe = np.where(d_debt <= 0, 1.0, d_debt)

    # sigma_V approx (E/V) * sigma_E
    sigma_v = (df["market_cap"] / v_safe) * df["equity_vol"]
    sigma_v = np.where(sigma_v <= 0, 0.01, sigma_v) # floor vol

    numerator = np.log(v_safe / d_safe) + (r + (sigma_v**2) / 2) * T
    denominator = sigma_v * np.sqrt(T)

    df["merton_dd"] = numerator / denominator
    # Probability of Default (PD) approximation: N(-DD)
    from scipy.stats import norm
    df["merton_pd"] = norm.cdf(-df["merton_dd"].clip(lower=-5, upper=5))

    # 9. Macro-Financial Interaction (Macro Sensitivity)
    # Sensitivity of Debt to Interest Rate hikes: (Total Liabilities / Total Assets) * Interest Rate
    # Here we use Debt Ratio as a proxy for sensitivity to credit tightening.
    df["macro_debt_exposure"] = df["debt_ratio"] * r
    # Sensitivity to Liquidity Shocks: (Current Liabilities - Cash) / EBITDA
    # High value = vulnerable to credit crunch.
    ebitda = df["ebit"] # proxy for ebitda
    ebitda_safe = np.where(ebitda == 0, 1.0, ebitda)
    df["liquidity_stress_exposure"] = (df["current_liabilities"] - df[cash_col]) / ebitda_safe

    # 10. Springate & Zmijewski
    ebt = df["ebit"] - df["interest_expense"]
    df["springate_s_score"] = (1.03 * df["working_capital_to_assets"] +
                               3.07 * df["ebit_to_assets"] +
                               0.66 * np.where(df["current_liabilities"] == 0, 0.0, ebt / df["current_liabilities"]) +
                               0.40 * np.where(df["total_assets"] == 0, 0.0, df["net_revenue"] / df["total_assets"]))
    df["springate_distressed"] = (df["springate_s_score"] < 0.862).astype(int)
    
    df["zmijewski_x_score"] = (-4.3 - 4.5 * df["roa"] + 5.7 * df["debt_ratio"] - 0.004 * df["current_ratio"].clip(upper=999.0))
    df["zmijewski_distressed"] = (df["zmijewski_x_score"] > 0).astype(int)
    
    # Clean up
    df.replace([np.inf, -np.inf], 9999.0, inplace=True)
    df.fillna(0.0, inplace=True)
    
    save_csv(df, config.FEATURES_FILE)
    logger.info(f"✅ Refined features saved to {config.FEATURES_FILE}")
    return True

def main():
    compute_financial_features()

if __name__ == "__main__":
    main()
