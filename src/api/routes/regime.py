# -*- coding: utf-8 -*-
"""
🌊 FINVISTA: REGIME ANALYSIS ROUTES
=====================================
FastAPI delivery layer cho Market Regime Analysis.
Exposes HMM market regime state và RegimeDetector signals.

Endpoints:
    GET /api/regime/market              → HMM market regime hiện tại (VNINDEX)
    GET /api/regime/{ticker}            → Regime analysis cho một mã cụ thể
    GET /api/regime/{ticker}/indicators → Technical indicators đầy đủ

Author: samvo
Version: 1.0
"""

from fastapi import APIRouter, Query
from src.core.utils import logger

router = APIRouter(tags=["regime-analysis"])


@router.get("/api/regime/market")
def get_market_regime():
    """
    Lấy Market Regime hiện tại của VNINDEX dựa trên HMM 4-state model.

    Trả về:
    - regime: BULLISH_VOL_EXPANSION | BULLISH_LOW_VOL | BEARISH_CRISIS | SIDEWAYS
    - confidence: xác suất state hiện tại [0, 1]
    - bias: LONG_CW | SHORT_CW | NEUTRAL | AVOID
    - description: mô tả trạng thái
    """
    try:
        from src.modules.regime_analysis.indicators.hmm_regime import calculate_vnindex_regime
        regime = calculate_vnindex_regime(days=1250)
        return {
            "status": "ok",
            "source": "HMM 4-state Gaussian Model (VNINDEX 5yr)",
            **regime,
        }
    except Exception as e:
        logger.warning(f"⚠️ [RegimeRoute] HMM failed: {e}. Using fallback.")
        return {
            "status": "fallback",
            "regime": "UNKNOWN",
            "confidence": 0.0,
            "bias": "NEUTRAL",
            "description": f"Không thể tính toán regime: {e}",
        }


@router.get("/api/regime/{ticker}")
def get_ticker_regime(
    ticker: str,
    days: int = Query(default=252, ge=60, le=1250, description="Số ngày dữ liệu để phân tích"),
):
    """
    Phân tích Market Regime cho một mã cổ phiếu cụ thể.

    Trả về:
    - current_regime: trạng thái HMM hiện tại
    - garch_volatility: dự báo biến động GARCH 1 bước
    - momentum_signals: multi-timeframe EMA signals
    - regime_recommendation: khuyến nghị giao dịch dựa trên regime
    """
    ticker_clean = ticker.upper().strip()

    result: dict = {
        "ticker": ticker_clean,
        "period_days": days,
    }

    # 1. GARCH Volatility Forecast
    try:
        from src.modules.regime_analysis.indicators.garch_volatility_forecaster import (
            GARCHVolatilityForecaster,
        )
        forecaster = GARCHVolatilityForecaster()
        garch_result = forecaster.forecast(ticker=ticker_clean, days=days)
        result["garch_volatility"] = garch_result
    except Exception as e:
        logger.debug(f"[RegimeRoute] GARCH forecast failed for {ticker_clean}: {e}")
        result["garch_volatility"] = {"error": str(e)}

    # 2. Multi-TF EMA Momentum
    try:
        from src.modules.regime_analysis.indicators.multi_tf_ema import calculate_multi_tf_ema
        ema_result = calculate_multi_tf_ema(ticker=ticker_clean, days=days)
        result["momentum_signals"] = ema_result
    except Exception as e:
        logger.debug(f"[RegimeRoute] EMA momentum failed for {ticker_clean}: {e}")
        result["momentum_signals"] = {"error": str(e)}

    # 3. Regime Recommendation
    try:
        from src.modules.regime_analysis.indicators.regime_detector import RegimeDetector
        detector = RegimeDetector()
        regime_data = detector.detect(ticker=ticker_clean, lookback_days=days)
        result["regime_detector"] = regime_data

        # Build recommendation
        regime_label = regime_data.get("regime", "UNKNOWN")
        if regime_label in ("BULLISH_VOL_EXPANSION", "BULLISH_LOW_VOL"):
            recommendation = "LONG — Xu hướng tăng, phù hợp mua CW CALL"
        elif regime_label == "BEARISH_CRISIS":
            recommendation = "AVOID / SHORT — Thị trường đang giảm mạnh"
        else:
            recommendation = "NEUTRAL — Sideways, chờ tín hiệu rõ hơn"

        result["regime_recommendation"] = recommendation
    except Exception as e:
        logger.debug(f"[RegimeRoute] RegimeDetector failed for {ticker_clean}: {e}")
        result["regime_detector"] = {"error": str(e)}
        result["regime_recommendation"] = "UNKNOWN"

    return result


@router.get("/api/regime/{ticker}/indicators")
def get_ticker_indicators(
    ticker: str,
    days: int = Query(default=252, ge=60, le=1250, description="Số ngày dữ liệu"),
):
    """
    Lấy toàn bộ technical indicators cho một mã.

    Bao gồm: GARCH, HMM state probabilities, Kalman Filter trend, EMA multi-TF.
    """
    ticker_clean = ticker.upper().strip()
    result: dict = {"ticker": ticker_clean, "period_days": days, "indicators": {}}

    # GARCH EVT VaR
    try:
        from src.modules.regime_analysis.indicators.garch_evt_var import calculate_garch_evt_var
        result["indicators"]["garch_evt_var"] = calculate_garch_evt_var(
            ticker=ticker_clean, days=days
        )
    except Exception as e:
        result["indicators"]["garch_evt_var"] = {"error": str(e)}

    # Kalman Filter
    try:
        from src.modules.regime_analysis.indicators.kalman_filter import KalmanFilter
        kf = KalmanFilter()
        result["indicators"]["kalman_trend"] = kf.estimate(ticker=ticker_clean, days=days)
    except Exception as e:
        result["indicators"]["kalman_trend"] = {"error": str(e)}

    # Volatility Models
    try:
        from src.modules.regime_analysis.indicators.volatility_models import (
            calculate_realized_volatility,
        )
        result["indicators"]["realized_volatility"] = calculate_realized_volatility(
            ticker=ticker_clean, days=days
        )
    except Exception as e:
        result["indicators"]["realized_volatility"] = {"error": str(e)}

    return result
