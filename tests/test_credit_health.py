import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from src.modules.credit_risk.service import CreditRiskService

def test_get_credit_health_banking_profile():
    # ACB is predefined in BANK_PROFILES
    res = CreditRiskService.get_credit_health("ACB")
    assert res["ticker"] == "ACB"
    assert res["is_bank"] is True
    assert res["credit_metrics"]["risk_zone"] == "SAFE (GREEN)"

def test_get_credit_health_caching():
    # First call will fetch or return static profile
    res1 = CreditRiskService.get_credit_health("TCB")
    
    # Modify cache directly to verify it returns from cache
    from src.modules.credit_risk.service import _cache
    assert "TCB" in _cache
    _cache["TCB"]["data"]["credit_metrics"]["risk_zone"] = "CACHED_ZONE"
    
    res2 = CreditRiskService.get_credit_health("TCB")
    assert res2["credit_metrics"]["risk_zone"] == "CACHED_ZONE"
    
    # Restore
    del _cache["TCB"]

def test_scan_tickers():
    tickers = ["TCB", "ACB", "NON_EXISTENT_TICKER"]
    with patch("src.modules.credit_risk.service.CreditRiskService.get_credit_health") as mock_get:
        mock_get.side_effect = [
            {"ticker": "TCB", "is_bank": True},
            {"ticker": "ACB", "is_bank": True},
            Exception("Not found")
        ]
        results = CreditRiskService.scan_tickers(tickers, limit=50)
        assert len(results) == 3
        assert results[0]["ticker"] == "TCB"
        assert results[1]["ticker"] == "ACB"
        assert "error" in results[2]
        assert results[2]["ticker"] == "NON_EXISTENT_TICKER"
