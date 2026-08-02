# -*- coding: utf-8 -*-
"""
🏦 FINVISTA: FINANCIAL INSTITUTIONS (BANKS/SEC/INS) HEALTH GATE
=============================================================
Specialized pipeline for evaluating Banks, Securities, and Insurance companies.
These are excluded from the main industrial distress pipeline (Altman/XGBoost).

Workflow:
  1. Filter for Financial Institutions (Banks, Securities, Insurance).
  2. Crawl financial ratios using vnstock.api.
  3. Apply CAMELS-lite (Banks) or Peer-Relative (Sec/Ins) scoring.
  4. Export to data/financial_health_report.csv.

Author: samvo
"""

import os
import sys
import pandas as pd
import time
import random
from typing import List, Dict, Any

# Ensure project root is on PYTHONPATH
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.core.utils import logger, save_json
from src.core import config
from src.modules.credit_risk.etl.inspect_companies import get_companies_data
from src.modules.credit_risk.models.bank_scoring import score_bank_health, get_bank_metrics_from_df
from src.modules.credit_risk.models.fi_scoring import score_securities_health, score_insurance_health, get_fi_metrics_from_df

try:
    from vnstock import Vnstock
except ImportError:
    Vnstock = None

FINANCIAL_REPORT_FILE = os.path.join(config.DATA_DIR, "financial_health_report.csv")

def get_financial_tickers() -> pd.DataFrame:
    """Identifies and returns tickers of banks, securities, insurance, and other financial services."""
    df = get_companies_data()
    
    # 1. Filter by Exchange
    if "exchange" in df.columns:
        df = df[df["exchange"].isin(config.TARGET_EXCHANGES)]
        
    # 2. Keywords for financial sectors
    bank_kw = ["Ngân hàng", "Bank"]
    sec_kw = ["Chứng khoán", "Securities"]
    ins_kw = ["Bảo hiểm", "Insurance"]
    fin_kw = ["Tài chính", "Quỹ", "Finance", "Investment"]
    
    def detect_subsector(row):
        name = str(row.get("company_name", "")).lower()
        industry = str(row.get("industry", "")).lower()
        
        if any(kw.lower() in name or kw.lower() in industry for kw in bank_kw):
            return "Banking"
        if any(kw.lower() in name or kw.lower() in industry for kw in sec_kw):
            return "Securities"
        if any(kw.lower() in name or kw.lower() in industry for kw in ins_kw):
            return "Insurance"
        if any(kw.lower() in name or kw.lower() in industry for kw in fin_kw):
            return "Financial Services"
        return None

    df["subsector"] = df.apply(detect_subsector, axis=1)
    fi_df = df[df["subsector"].notnull()].copy()
    
    fi_df["ticker"] = fi_df["ticker"].str.strip().str.upper()
    return fi_df

def crawl_fi_health(df_tickers: pd.DataFrame):
    """Crawls and scores financial health for the identified FIs."""
    if Vnstock is None:
        logger.error("❌ vnstock library not found. Cannot crawl financial health.")
        return

    v = Vnstock()
    results = []
    
    total = len(df_tickers)
    logger.info(f"🚀 Starting Financial Health Gate crawl for {total} institutions...")

    for idx, row in df_tickers.iterrows():
        ticker = row["ticker"]
        subsector = row["subsector"]
        logger.info(f"🔄 Processing {ticker} ({subsector}) - {idx+1}/{total}")
        
        try:
            # 1. Fetch Ratios
            stock = v.stock(symbol=ticker)
            df_ratios = stock.finance.ratio(period='year')
            
            health_data = {
                "ticker": ticker,
                "subsector": subsector,
                "score_fa": 15.0, # Default
                "nim": None, "npl": None, "casa": None, "car": None,
                "roe": None, "roa": None,
                "status": "GREEN"
            }
            
            if not df_ratios.empty:
                latest_col = df_ratios.columns[-1]
                
                if subsector == "Banking":
                    metrics = get_bank_metrics_from_df(df_ratios, ticker)
                    score = score_bank_health(metrics)
                    health_data.update({
                        "score_fa": (score / 100.0) * 18.5,
                        "nim": metrics.get("nim"),
                        "npl": metrics.get("npl"),
                        "casa": metrics.get("casa"),
                        "car": metrics.get("car")
                    })
                    # Hard gate check for banks
                    npl = metrics.get("npl")
                    car = metrics.get("car")
                    if (npl is not None and npl > 0.05) or (car is not None and car < 0.08):
                        health_data["status"] = "RED"
                        health_data["score_fa"] = 2.0
                elif subsector == "Securities":
                    metrics = get_fi_metrics_from_df(df_ratios)
                    score = score_securities_health(metrics)
                    health_data.update({
                        "score_fa": (score / 100.0) * 18.5,
                        "roe": metrics.get("roe"),
                        "roa": metrics.get("roa")
                    })
                    if metrics.get("roe", 0) < 0.02: # Heavy warning for very low ROE
                        health_data["status"] = "RED"
                elif subsector == "Insurance":
                    metrics = get_fi_metrics_from_df(df_ratios)
                    score = score_insurance_health(metrics)
                    health_data.update({
                        "score_fa": (score / 100.0) * 18.5,
                        "roe": metrics.get("roe"),
                        "roa": metrics.get("roa")
                    })
                    if metrics.get("roe", 0) < 0.02:
                        health_data["status"] = "RED"
                else:
                    # General Financial Services (Funds, etc.)
                    metrics = get_fi_metrics_from_df(df_ratios)
                    roe = metrics.get("roe", 0)
                    health_data.update({"roe": roe, "roa": metrics.get("roa")})
                    if roe > 0.15: health_data["score_fa"] = 18.0
                    elif roe > 0.05: health_data["score_fa"] = 15.0
                    else: health_data["score_fa"] = 10.0
                    
            results.append(health_data)
            
            # Be polite
            time.sleep(random.uniform(1.0, 2.0))
            
        except Exception as e:
            logger.error(f"⚠️ Failed to process {ticker}: {e}")
            results.append({"ticker": ticker, "subsector": subsector, "score_fa": 15.0, "status": "UNKNOWN"})

    # Export
    final_df = pd.DataFrame(results)
    final_df.to_csv(FINANCIAL_REPORT_FILE, index=False)
    logger.info(f"✅ Financial health report saved to {FINANCIAL_REPORT_FILE}")

def main():
    fi_tickers = get_financial_tickers()
    if fi_tickers.empty:
        logger.warning("No financial institutions found to evaluate.")
        return
    crawl_fi_health(fi_tickers)

if __name__ == "__main__":
    main()
