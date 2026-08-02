import pytest
from unittest.mock import patch, MagicMock
from src.modules.cw_pricing.prompts.analyst_prompt import build_analyst_prompt

def test_build_analyst_prompt():
    # Mock WarrantService.get_opportunities
    mock_opps = {
        "status": "ok",
        "recommendations": [
            {
                "warrant_symbol": "CHPG2301",
                "underlying_symbol": "HPG",
                "issuer": "SSI",
                "market_price": 1200.0,
                "price_change_pct": 1.5,
                "implied_volatility_pct": 45.0,
                "historical_volatility_pct": 35.0,
                "delta": 0.45,
                "theta_daily_burn": -10.0,
                "days_to_maturity": 60,
                "composite_g_score": 85.0,
                "recommendation_signal": "BUY"
            }
        ]
    }
    
    # Mock get_ticker_regime
    mock_regime = {
        "regime_recommendation": "BULLISH_LOW_VOL",
        "regime_detector": {
            "regime": "BULLISH_LOW_VOL"
        }
    }
    
    # Mock NewsImpactService
    mock_sentiment = {
        "sentiment_score": 0.25
    }
    mock_ml_signal = {
        "outperform_probability": 0.65
    }
    
    mock_market_regime = {
        "regime": "BULLISH_LOW_VOL",
        "confidence": 0.85
    }
    
    with patch("src.modules.cw_pricing.prompts.analyst_prompt.WarrantService.get_opportunities", return_value=mock_opps), \
         patch("src.modules.cw_pricing.prompts.analyst_prompt.get_ticker_regime", return_value=mock_regime), \
         patch("src.api.routes.regime.get_market_regime", return_value=mock_market_regime), \
         patch("src.modules.cw_pricing.prompts.analyst_prompt.NewsImpactService.get_news_impact", return_value=mock_sentiment), \
         patch("src.modules.cw_pricing.prompts.analyst_prompt.NewsImpactService.get_ml_signal", return_value=mock_ml_signal):
         
        res = build_analyst_prompt("HPG")
        assert "prompt" in res
        assert "data_injected" in res
        assert res["data_injected"]["underlying_ticker"] == "HPG"
        assert len(res["cw_candidates"]) == 1
        assert res["cw_candidates"][0]["symbol"] == "CHPG2301"
        assert "CHPG2301" in res["prompt"]
