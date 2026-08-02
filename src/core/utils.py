# -*- coding: utf-8 -*-
"""
Utility module for the Financial Distress Prediction Pipeline.
Contains logging configurations, file helpers, and checkpoint utilities.
"""

import os
import json
import logging
import time
import random
import pandas as pd
from typing import Any, Dict, List

# Custom Formatter to match the screenshot: "14:21:50 | INFO  | Message"
class CustomFormatter(logging.Formatter):
    def format(self, record):
        log_time = time.strftime("%H:%M:%S", time.localtime(record.created))
        return f"{log_time} | {record.levelname:<5} | {record.getMessage()}"

def get_logger(name: str = "financial_distress") -> logging.Logger:
    """Configures and returns a custom formatted logger."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        # Console Handler
        ch = logging.StreamHandler()
        ch.setFormatter(CustomFormatter())
        logger.addHandler(ch)
        
        # File Handler
        from src.core import config
        file_log_path = os.path.join(config.LOG_DIR, "pipeline.log")
        fh = logging.FileHandler(file_log_path, encoding="utf-8")
        fh.setFormatter(CustomFormatter())
        logger.addHandler(fh)
        
    return logger

logger = get_logger()

def load_json(file_path: str) -> Any:
    """Safely loads a JSON file."""
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading JSON from {file_path}: {e}")
            return None
    return None

def save_json(data: Any, file_path: str) -> bool:
    """Safely saves data to a JSON file."""
    try:
        # Ensure parent directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        logger.error(f"Error saving JSON to {file_path}: {e}")
        return False

def load_csv(file_path: str) -> pd.DataFrame:
    """Safely loads a CSV file."""
    if os.path.exists(file_path):
        try:
            return pd.read_csv(file_path, encoding="utf-8")
        except Exception as e:
            logger.error(f"Error loading CSV from {file_path}: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

def save_csv(df: pd.DataFrame, file_path: str) -> bool:
    """Safely saves a pandas DataFrame to a CSV file."""
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        df.to_csv(file_path, index=False, encoding="utf-8")
        return True
    except Exception as e:
        logger.error(f"Error saving CSV to {file_path}: {e}")
        return False

def random_sleep(min_sec: float = 1.0, max_sec: float = 2.5):
    """Sleeps for a random duration to prevent API blocking."""
    duration = random.uniform(min_sec, max_sec)
    time.sleep(duration)

class CheckpointManager:
    """Manages crawl state to allow resuming from failures."""
    def __init__(self, checkpoint_file: str):
        self.checkpoint_file = checkpoint_file
        self.state = self.load()

    def load(self) -> Dict[str, Any]:
        state = load_json(self.checkpoint_file)
        if state is None:
            state = {
                "last_processed_index": 0,
                "completed_tickers": [],
                "failed_tickers": {}
            }
        return state

    def save(self, index: int, ticker: str, status: str = "success", error_msg: str = ""):
        self.state["last_processed_index"] = index
        if status == "success":
            if ticker not in self.state["completed_tickers"]:
                self.state["completed_tickers"].append(ticker)
            if ticker in self.state["failed_tickers"]:
                del self.state["failed_tickers"][ticker]
        else:
            self.state["failed_tickers"][ticker] = {
                "error": error_msg,
                "timestamp": time.time(),
                "attempts": self.state["failed_tickers"].get(ticker, {}).get("attempts", 0) + 1
            }
        save_json(self.state, self.checkpoint_file)

    def get_progress(self) -> int:
        return self.state["last_processed_index"]

    def get_completed(self) -> List[str]:
        return self.state["completed_tickers"]

    def get_failed(self) -> Dict[str, Any]:
        return self.state["failed_tickers"]
