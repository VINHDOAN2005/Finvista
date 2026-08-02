# -*- coding: utf-8 -*-
"""
Config module for the Financial Distress Prediction Pipeline.
Defines paths and configuration settings.
"""

import os
from dotenv import load_dotenv
import pandas as pd

# Fix lỗi hiển thị bảng Active Positions trên Terminal
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 125)        # Ép độ rộng cố định để không rớt chữ
pd.set_option('display.max_colwidth', 30)  
pd.set_option('display.unicode.east_asian_width', True)

# Load environment variables from .env file
load_dotenv()

# Project Root Directory (two levels up from src/common/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Trained model artifacts (.pkl, JSON configs) — repo root artifacts/
ARTIFACTS_DIR = os.path.join(BASE_DIR, "artifacts")
MODELS_DIR = ARTIFACTS_DIR  # backward-compatible alias

# Organized by domain modules
CREDIT_RISK_DIR = os.path.join(ARTIFACTS_DIR, "credit_risk")
CW_PRICING_DIR = os.path.join(ARTIFACTS_DIR, "cw_pricing")
REGIME_ANALYSIS_DIR = os.path.join(ARTIFACTS_DIR, "regime_analysis")

# Credit Risk models
BEST_DISTRESS_MODEL = os.path.join(CREDIT_RISK_DIR, "best_distress_model.pkl")
SCALER_ARTIFACT = os.path.join(CREDIT_RISK_DIR, "scaler.pkl")
FEATURE_NAMES_ARTIFACT = os.path.join(CREDIT_RISK_DIR, "feature_names.pkl")
THRESHOLD_CONFIG = os.path.join(CREDIT_RISK_DIR, "threshold_config.json")
BEST_MODEL_PARAMS = os.path.join(CREDIT_RISK_DIR, "best_model_params.json")
SHAP_FEATURE_IMPORTANCE = os.path.join(CREDIT_RISK_DIR, "shap_feature_importance.json")

# CW Pricing models
ML_PRICING_MODEL = os.path.join(CW_PRICING_DIR, "ml_pricing_model.pkl")
ML_HYBRID_VOL_MODEL = os.path.join(CW_PRICING_DIR, "ml_hybrid_vol_model.pkl")

# Regime Analysis models
XGBOOST_REGIME_DIR = REGIME_ANALYSIS_DIR  # For pattern matching xgboost_regime_*.pkl

# Ensure all directories exist
for path in [ARTIFACTS_DIR, CREDIT_RISK_DIR, CW_PRICING_DIR, REGIME_ANALYSIS_DIR]:
    os.makedirs(path, exist_ok=True)

# Data Directory Structure
DATA_DIR = os.path.join(BASE_DIR, "data", "raw", "financial_distress")
RAW_DATA_DIR = os.path.join(DATA_DIR, "raw")
PROCESSED_DATA_DIR = os.path.join(DATA_DIR, "processed")
FINAL_DATA_DIR = os.path.join(DATA_DIR, "final")
LOG_DIR = os.path.join(BASE_DIR, "logs")

# Ensure all directories exist
for path in [DATA_DIR, RAW_DATA_DIR, PROCESSED_DATA_DIR, FINAL_DATA_DIR, LOG_DIR]:
    os.makedirs(path, exist_ok=True)

# File Paths
COMPANIES_LIST_FILE = os.path.join(DATA_DIR, "companies_list.json")
FILTERED_COMPANIES_FILE = os.path.join(DATA_DIR, "filtered_companies.json")
RAW_FINANCIALS_FILE = os.path.join(RAW_DATA_DIR, "raw_financials.json")
CLEANED_FINANCIALS_FILE = os.path.join(PROCESSED_DATA_DIR, "cleaned_financials.csv")
FEATURES_FILE = os.path.join(PROCESSED_DATA_DIR, "financial_features.csv")
LABELED_DATA_FILE = os.path.join(PROCESSED_DATA_DIR, "labeled_financial_data.csv")
FINAL_DATASET_FILE = os.path.join(FINAL_DATA_DIR, "financial_distress_dataset.csv")

# Pipeline Configuration
TARGET_EXCHANGES = ["HOSE", "HNX", "UPCOM"]
START_YEAR = 2018
END_YEAR = 2025

# Ticker group filter: "VN30", "VN100", or "ALL" (to crawl all listed companies)
# Using "ALL" to crawl all 1,467 non-financial listed corporations on HOSE, HNX, UPCOM.
TICKER_GROUP = "ALL"

# Set to True to generate high-fidelity simulated/mock data instantly (perfect for fast testing)
USE_MOCK = False

# Crawling & Ingestion Settings
CRAWL_CHECKPOINT_INTERVAL = 25  # Save checkpoint every 25 companies
MAX_RETRIES = 3
MIN_DELAY = 1.0
MAX_DELAY = 2.5

# Excluded Financial Industry Sectors (Sectors with distinct report structures)
# Matches real vnstock v4 industry_name taxonomy from symbols_by_industries()
EXCLUDED_SECTORS = [
    "Ngân hàng",
    "Chứng khoán",
    "Bảo hiểm",
    "Quỹ đầu tư",
    "Công ty tài chính",
    "Tài chính khác",   # appears in vnstock v4 industry list
    "Banking",
    "Securities",
    "Insurance",
    "Investment Funds",
    "Financial Services"
]
