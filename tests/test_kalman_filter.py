import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock
from src.modules.regime_analysis.indicators.kalman_filter import KalmanFilter

def test_kalman_filter_insufficient_data():
    kf = KalmanFilter()
    with patch("pandas.read_sql") as mock_read_sql:
        mock_read_sql.return_value = pd.DataFrame()
        result = kf.estimate("VNM")
        assert result["signal"] == "NEUTRAL"
        assert result["latest_price"] == 0.0
        assert "error" in result

def test_kalman_filter_bullish_trend():
    kf = KalmanFilter()
    # Create an upward trend
    mock_df = pd.DataFrame({
        "date": pd.date_range(start="2026-01-01", periods=10),
        "close": [10.0, 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 10.8, 10.9]
    })
    with patch("pandas.read_sql") as mock_read_sql:
        mock_read_sql.return_value = mock_df
        result = kf.estimate("VNM")
        assert result["signal"] in ("BULLISH", "BEARISH", "NEUTRAL")
        assert result["latest_price"] == 10.9
        assert result["signal"] == "BULLISH"

def test_kalman_filter_bearish_trend():
    kf = KalmanFilter()
    # Create a downward trend
    mock_df = pd.DataFrame({
        "date": pd.date_range(start="2026-01-01", periods=10),
        "close": [10.9, 10.8, 10.7, 10.6, 10.5, 10.4, 10.3, 10.2, 10.1, 10.0]
    })
    with patch("pandas.read_sql") as mock_read_sql:
        mock_read_sql.return_value = mock_df
        result = kf.estimate("VNM")
        assert result["signal"] == "BEARISH"
