# -*- coding: utf-8 -*-
"""
Step 3: Compute Financial Ratios and Features.
Calculates liquidity, profitability, leverage, growth indicators,
Altman Z''-Score, Springate S-Score, and Zmijewski X-Score inputs.
"""

import os
import pandas as pd
import numpy as np
from src.common.utils import logger, load_csv, save_csv
from src.common import config

def compute_financial_features():
    logger.info("🎬 STEP 3: Computing financial ratios and features...")
    
    if not os.path.exists(config.CLEANED_FINANCIALS_FILE):
        logger.error(f"❌ Structured financial data not found: {config.CLEANED_FINANCIALS_FILE}")
        return False
        
    df = load_csv(config.CLEANED_FINANCIALS_FILE)
    if df.empty:
        logger.error("❌ Cleaned dataset is empty!")
        return False
        
    # Sort by ticker and year to compute lag/growth variables
    df.sort_values(by=["ticker", "year"], inplace=True)
    
    logger.info("⚙️ Calculating liquidity, profitability, leverage, and distress-model ratios...")
    
    # 1. Liquidity Indicators
    df["current_ratio"] = np.where(df["current_liabilities"] == 0, 9999.0, df["current_assets"] / df["current_liabilities"])
    df["working_capital"] = df["current_assets"] - df["current_liabilities"]
    df["working_capital_to_assets"] = np.where(df["total_assets"] == 0, 0.0, df["working_capital"] / df["total_assets"])
    df["ocf_to_current_liabilities"] = np.where(df["current_liabilities"] == 0, 0.0, df["operating_cash_flow"] / df["current_liabilities"])
    # Cash ratio: Tiền & tương đương / Nợ ngắn hạn
    cash_col = "cash_and_equivalents" if "cash_and_equivalents" in df.columns else "current_assets"
    df["cash_ratio"] = np.where(df["current_liabilities"] == 0, 9999.0, df[cash_col] / df["current_liabilities"])
    # OCF-to-total-debt (dòng tiền so với toàn bộ nợ)
    df["ocf_to_total_debt"] = np.where(df["total_liabilities"] == 0, 0.0, df["operating_cash_flow"] / df["total_liabilities"])
    
    # 2. Profitability Indicators
    df["roa"] = np.where(df["total_assets"] == 0, 0.0, df["profit_after_tax"] / df["total_assets"])
    df["roe"] = np.where(df["total_equity"] == 0, 0.0, df["profit_after_tax"] / df["total_equity"])
    df["operating_margin"] = np.where(df["net_revenue"] == 0, 0.0, df["ebit"] / df["net_revenue"])
    df["ebit_to_assets"] = np.where(df["total_assets"] == 0, 0.0, df["ebit"] / df["total_assets"])
    
    # 3. Leverage Indicators
    df["debt_ratio"] = np.where(df["total_assets"] == 0, 0.0, df["total_liabilities"] / df["total_assets"])
    df["equity_multiplier"] = np.where(df["total_equity"] == 0, 9999.0, df["total_assets"] / df["total_equity"])
    df["ebit_to_interest"] = np.where(df["interest_expense"] == 0, 9999.0, df["ebit"] / df["interest_expense"])
    # Alias ICR (Interest Coverage Ratio) — tên chuẩn dùng trong nghiên cứu
    df["icr"] = df["ebit_to_interest"]
    
    # 4. Size and Growth Indicators
    # Use natural log for company size (avoid log of negative assets, if any)
    df["company_size"] = np.where(df["total_assets"] <= 0, 0.0, np.log(df["total_assets"]))
    
    # Growth rates require comparison with the previous year's values
    df["revenue_growth"] = 0.0
    df["assets_growth"] = 0.0
    
    # Group by ticker to compute lag differences
    for ticker, group in df.groupby("ticker"):
        if len(group) > 1:
            rev_pct = group["net_revenue"].pct_change().fillna(0.0)
            assets_pct = group["total_assets"].pct_change().fillna(0.0)
            df.loc[group.index, "revenue_growth"] = rev_pct
            df.loc[group.index, "assets_growth"] = assets_pct
            
    # 5. Altman Z''-Score Components (Emerging Market Z''-Score formulation)
    # Z'' = 6.56*X1 + 3.26*X2 + 6.72*X3 + 1.05*X4
    df["altman_x1"] = df["working_capital_to_assets"]
    df["altman_x2"] = np.where(df["total_assets"] == 0, 0.0, df["retained_earnings"] / df["total_assets"])
    df["altman_x3"] = df["ebit_to_assets"]
    df["altman_x4"] = np.where(df["total_liabilities"] == 0, 9999.0, df["market_cap"] / df["total_liabilities"])
    
    df["altman_z_score"] = (6.56 * df["altman_x1"] + 
                            3.26 * df["altman_x2"] + 
                            6.72 * df["altman_x3"] + 
                            1.05 * df["altman_x4"])
    
    # 6. Springate S-Score (1978) — phù hợp nhất cho DNNY phi tài chính VN
    # S = 1.03*X1 + 3.07*X2 + 0.66*X3 + 0.4*X4
    # X1 = Working Capital / Total Assets
    # X2 = EBIT / Total Assets
    # X3 = EBT / Current Liabilities  (EBT ≈ EBIT - interest_expense)
    # X4 = Sales / Total Assets (Asset Turnover)
    ebt = df["ebit"] - df["interest_expense"] if "interest_expense" in df.columns else df["ebit"]
    springate_x1 = df["working_capital_to_assets"]
    springate_x2 = df["ebit_to_assets"]
    springate_x3 = np.where(df["current_liabilities"] == 0, 0.0, ebt / df["current_liabilities"])
    springate_x4 = np.where(df["total_assets"] == 0, 0.0, df["net_revenue"] / df["total_assets"])
    df["springate_s_score"] = (1.03 * springate_x1 +
                               3.07 * springate_x2 +
                               0.66 * springate_x3 +
                               0.40 * springate_x4)
    # Ngưỡng: S < 0.862 → kiệt quệ
    df["springate_distressed"] = (df["springate_s_score"] < 0.862).astype(int)
    logger.info("   ✅ Springate S-Score computed (threshold: 0.862)")
    
    # 7. Zmijewski X-Score (1984) — Probit-based model
    # X = -4.3 - 4.5*ROA + 5.7*Leverage - 0.004*Current_Ratio
    # X > 0 → nguy cơ kiệt quệ
    df["zmijewski_x_score"] = (-4.3
                               - 4.5 * df["roa"]
                               + 5.7 * df["debt_ratio"]
                               - 0.004 * df["current_ratio"].clip(upper=999.0))
    df["zmijewski_distressed"] = (df["zmijewski_x_score"] > 0).astype(int)
    logger.info("   ✅ Zmijewski X-Score computed (threshold: X > 0)")
    
    # Replace any infs or NaNs resulting from division issues
    df.replace([np.inf, -np.inf], 9999.0, inplace=True)
    df.fillna(0.0, inplace=True)
    
    # Save computed features
    save_csv(df, config.FEATURES_FILE)
    logger.info(f"✅ Financial features and ratios saved to {config.FEATURES_FILE}")
    logger.info(f"   📊 Columns in features file: {len(df.columns)}")
    # Log distress model summary
    s_distress_rate = df["springate_distressed"].mean() if "springate_distressed" in df.columns else 0
    z_distress_rate = df["zmijewski_distressed"].mean() if "zmijewski_distressed" in df.columns else 0
    logger.info(f"   📉 Springate distress rate : {s_distress_rate:.2%} of all records")
    logger.info(f"   📉 Zmijewski distress rate : {z_distress_rate:.2%} of all records")
    return True

def main():
    compute_financial_features()

if __name__ == "__main__":
    main()
