# -*- coding: utf-8 -*-
"""
📊 FINVISTA CREDIT RISK PIPELINE — STEP 7: EVALUATE MARKET HEALTH
=================================================================
Chạy suy luận hàng loạt (batch inference) với mô hình XGBoost đã huấn luyện
trên toàn bộ 1,533 doanh nghiệp niêm yết, xuất báo cáo sức khỏe tín dụng
thị trường (market_health_report.csv) phân loại GREEN / YELLOW / RED.

CLI: python run.py credit --evaluate

Author: samvo
"""

import os
import pandas as pd
import numpy as np
import joblib
from src.core.utils import logger, load_csv, save_csv
from src.core import config

def evaluate_market_health():
    logger.info("📡 RUNNING FULL-MARKET CREDIT HEALTH INFERENCE ENGINE (XGBOOST)")
    
    # 1. Load trained Model and Scaler
    model_path = config.BEST_DISTRESS_MODEL
    scaler_path = config.SCALER_ARTIFACT
    
    if not os.path.exists(model_path) or not os.path.exists(scaler_path):
        logger.error("❌ Trained model or scaler not found!")
        logger.info("💡 Please run model training first: python run_credit_risk.py --train")
        return False
        
    model = joblib.load(model_path)
    scaler = joblib.load(scaler_path)
    logger.info("🧠 Successfully loaded XGBoost early warning model and scaling matrix.")

    # 2. Load latest corporate features dataset
    dataset_file = config.FINAL_DATASET_FILE
    if not os.path.exists(dataset_file):
        logger.error(f"❌ Final processed financials dataset not found: {dataset_file}")
        return False
        
    df = load_csv(dataset_file)
    if df.empty:
        logger.error("❌ Dataset is empty!")
        return False
        
    logger.info(f"📊 Loaded {len(df)} historical corporate-year financial records.")

    # 3. Filter to get the latest reported year for EVERY company (to analyze current health)
    latest_records = df.sort_values("year").groupby("ticker").last().reset_index()
    logger.info(f"🎯 Filtered to the latest reported year for {len(latest_records)} unique corporations.")

    # Load corporate metadata to resolve KeyError and enrich the report
    metadata_file = os.path.join(config.DATA_DIR, "companies_list_ALL.json")
    name_map, exchange_map, industry_map = {}, {}, {}
    if os.path.exists(metadata_file):
        try:
            import json
            with open(metadata_file, "r", encoding="utf-8") as f:
                metadata_list = json.load(f)
                for item in metadata_list:
                    ticker = item.get("ticker")
                    if ticker:
                        name_map[ticker] = item.get("company_name", "N/A")
                        exchange_map[ticker] = item.get("exchange", "N/A")
                        industry_map[ticker] = item.get("industry", "N/A")
            logger.info(f"📂 Loaded corporate metadata for {len(name_map)} tickers from cache.")
        except Exception as me:
            logger.warning(f"⚠️ Failed to parse corporate metadata from JSON: {me}")
            
    latest_records["company_name"] = latest_records["ticker"].map(name_map).fillna("N/A")
    latest_records["exchange"] = latest_records["ticker"].map(exchange_map).fillna("N/A")
    latest_records["industry"] = latest_records["ticker"].map(industry_map).fillna("N/A")

    # 4. Prepare features for ML Model
    exclude_cols = {
        "ticker", "company_name", "year", "exchange", "industry", 
        "distress_label", "distress_label_next_year",
        "ebit_to_interest", "icr", "current_ratio", "total_equity",
        "springate_distressed", "zmijewski_distressed"
    }
    feature_cols = [c for c in latest_records.columns if c not in exclude_cols]
    
    X = latest_records[feature_cols].copy().astype(float)
    
    # 5. Execute full-market prediction
    try:
        X_scaled = scaler.transform(X)
        X_scaled_df = pd.DataFrame(X_scaled, columns=feature_cols)
        distress_probs = model.predict_proba(X_scaled_df)[:, 1]
    except Exception as e:
        logger.error(f"❌ Failed to run ML inference on market features: {e}")
        return False

    latest_records["ml_distress_probability"] = distress_probs
    
    # --- STEP 7.5: MACRO-ECONOMIC OVERLAY (Research Standard) ---
    # Global naming: inflation_rate, unemployment_rate, gdp_growth_rate, interbank_rate
    # Current values for Vietnam (proxy for 2024-2026)
    macro_context = {
        "inflation_rate": 0.041,      # 4.1%
        "unemployment_rate": 0.023,   # 2.3%
        "gdp_growth_rate": 0.065,     # 6.5%
        "interbank_rate": 0.052       # 5.2% (Hàn thử biểu thanh khoản hệ thống)
    }
    
    logger.info(f"🌐 Applying Macro-Economic Overlay (Standardized): Inflation {macro_context['inflation_rate']:.1%}, Interbank Rate {macro_context['interbank_rate']:.1%}")
    
    def apply_macro_adjustment(row):
        prob = row["ml_distress_probability"]
        
        # Rule 1: High Inflation + Low Interest Coverage = Increased Distress Risk
        icr = row.get("icr", 999.0)
        if macro_context["inflation_rate"] > 0.04 and icr < 2.0:
            prob += 0.05 # Add 5% risk penalty
            
        # Rule 2: Interbank Rate Stress (Liquidity Crunch)
        # High interbank rates punish companies with high short-term debt and low cash
        debt_ratio = row.get("debt_ratio", 0.0)
        cash_ratio = row.get("cash_ratio", 1.0) # We need to ensure cash_ratio is in the report
        if macro_context["interbank_rate"] > 0.05:
            if debt_ratio > 0.6 and cash_ratio < 0.2:
                prob += 0.08 # Heavy 8% penalty for liquidity-vulnerable firms
            elif debt_ratio > 0.4:
                prob += 0.03 # 3% penalty for moderately leveraged firms
            
        # Rule 3: Unemployment impact on Consumer sectors
        consumer_sectors = ["Bán lẻ", "Thực phẩm và đồ uống", "Du lịch và Giải trí"]
        if macro_context["unemployment_rate"] > 0.03 and row["industry"] in consumer_sectors:
            prob += 0.03 # Add 3% risk penalty
            
        return min(prob, 0.999) # Cap at 99.9%

    latest_records["adjusted_distress_probability"] = latest_records.apply(apply_macro_adjustment, axis=1)
    
    # 6. Apply Health Ratings (Traffic Light Logic) - Updated to use Adjusted Prob
    def determine_status(row):
        prob = row["adjusted_distress_probability"]
        z_score = row.get("altman_z_score", 3.0)
        
        # Red: Extremely high ML predicted distress or already bankrupt/deep under Altman red
        if prob >= 0.50 or z_score < 1.10:
            return "💥 RED (DANGER)"
        # Yellow: Grey zone of Altman, but ML probability is relatively safe
        elif z_score <= 2.60:
            return "⚠️ YELLOW (WARNING)"
        # Green: Strong balance sheet & low ML distress probability
        else:
            return "✅ GREEN (SAFE)"
            
    latest_records["health_status"] = latest_records.apply(determine_status, axis=1)

    # 7. Create beautiful corporate health report table
    report_cols = [
        "ticker", "company_name", "year", "exchange", "industry",
        "altman_z_score", "springate_s_score", "zmijewski_x_score",
        "ml_distress_probability", "health_status"
    ]
    report_df = latest_records[report_cols].copy()
    
    # Save full report to CSV
    report_file = os.path.join(config.DATA_DIR, "market_health_report.csv")
    save_csv(report_df, report_file)
    logger.info(f"💾 Full Market Health Report successfully saved to: {report_file}")

    # 8. Print Executive Summary
    total_cos = len(report_df)
    red_cos = len(report_df[report_df["health_status"] == "💥 RED (DANGER)"])
    yellow_cos = len(report_df[report_df["health_status"] == "⚠️ YELLOW (WARNING)"])
    green_cos = len(report_df[report_df["health_status"] == "✅ GREEN (SAFE)"])
    
    logger.info("📈 FINVISTA CORPORATE HEALTH AUDIT - MARKET EXECUTIVE SUMMARY:")
    logger.info(f"   • Total Corporations Audited  : {total_cos} companies")
    logger.info(f"   • ✅ GREEN (SAFE Zone)        : {green_cos} companies ({green_cos/total_cos:.2%})")
    logger.info(f"   • ⚠️ YELLOW (Grey/Warning Zone): {yellow_cos} companies ({yellow_cos/total_cos:.2%})")
    logger.info(f"   • 💥 RED (DANGER Zone)        : {red_cos} companies ({red_cos/total_cos:.2%})")

    # 9. Top 10 Most Vulnerable Companies
    logger.info("🚨 TOP 10 DOANH NGHIỆP CÓ RỦI RO KIỆT QUỆ CAO NHẤT THỊ TRƯỜNG CHỨNG KHOÁN:")
    logger.info(f"{'Ticker':<8} | {'Tên Công Ty':<45} | {'Năm Tài Khóa':<12} | {'Z-Score':<8} | {'ML Prob':<8}")
    
    danger_sorted = report_df.sort_values("ml_distress_probability", ascending=False).head(10)
    for idx, r in danger_sorted.iterrows():
        name_trunc = r['company_name'][:43] + "..." if len(r['company_name']) > 43 else r['company_name']
        logger.info(f"{r['ticker']:<8} | {name_trunc:<45} | {int(r['year']):<12} | {r['altman_z_score']:<8.2f} | {r['ml_distress_probability']:.1%}")
    logger.info("")
    
    return True

if __name__ == "__main__":
    evaluate_market_health()
