import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from src.modules.cw_pricing.service import WarrantService
from src.core.database import MarketOpportunity

def test_simulate_scenarios_success():
    # Mock database record
    mock_opp = MarketOpportunity(
        symbol="CACB2511",
        underlying="ACB",
        underlying_price=22600.0,
        strike_price=19832.0,
        days_to_maturity=87,
        implied_volatility_pct=30.48,
        ratio="1:1",
        price=1900.0,
        volume=50000.0,
        premium_pct=15.5,
        gearing=4.2,
        delta=0.65,
        theta_burn_day=-12.5
    )

    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = mock_opp

    with patch("src.modules.cw_pricing.service.SessionLocal", return_value=mock_db):
        res = WarrantService.simulate_scenarios("CACB2511")
        assert res["symbol"] == "CACB2511"
        assert res["underlying_symbol"] == "ACB"
        assert res["volume"] == 50000.0
        assert res["premium_pct"] == 15.5
        assert res["effective_gearing"] == 4.2
        assert res["delta"] == 0.65
        assert res["theta_daily_burn"] == -12.5
        assert len(res["scenarios"]) > 0

def test_get_history_success():
    # Mock data frame returned by analyze_historical_warrant
    mock_df = pd.DataFrame([
        {
            "date": pd.Timestamp("2026-06-25"),
            "close_cw": 1900.0,
            "chg_cw": 1.5,
            "close_stock": 22600.0,
            "chg_stock": 0.5,
            "iv": 0.3048,
            "hv": 0.2414,
            "delta": 0.65,
            "gearing": 4.2,
            "theta_burn": -0.0125,
            "open": 1850.0,
            "high": 1950.0,
            "low": 1800.0,
            "volume": 25000.0,
            "theo_price_hv": 1880.0,
            "pricing_gap_pct": 1.06
        }
    ])

    with patch("src.modules.cw_pricing.service.analyze_historical_warrant", return_value=mock_df):
        res = WarrantService.get_history("CACB2511", days=1)
        assert res["symbol"] == "CACB2511"
        assert len(res["history"]) == 1
        record = res["history"][0]
        assert record["date"] == "2026-06-25"
        assert record["warrant_price"] == 1900.0
        assert record["warrant_ohlc"]["open"] == 1850.0
        assert record["warrant_ohlc"]["high"] == 1950.0
        assert record["warrant_ohlc"]["low"] == 1800.0
        assert record["warrant_ohlc"]["volume"] == 25000.0
        assert record["theoretical_price"] == 1880.0
        assert record["pricing_gap_pct"] == 1.06
