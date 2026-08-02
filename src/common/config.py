# -*- coding: utf-8 -*-
"""
Config module for the Financial Distress Prediction Pipeline.
Defines paths and configuration settings.
"""

import os

# Project Root Directory (two levels up from src/common/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Data Directory Structure
DATA_DIR = os.path.join(BASE_DIR, "data", "financial_distress")
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
