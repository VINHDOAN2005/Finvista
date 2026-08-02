# -*- coding: utf-8 -*-
"""
🏆 FINVISTA: CORPORATE CREDIT HEALTH & SYSTEMIC RISK ROUTES
=============================================================
FastAPI delivery layer for bankruptcy prediction, financial health assessment,
and market contagion / systemic risk analysis.

Endpoints:
    GET /api/credit-health/{ticker}   → XGBoost credit health for one ticker
    GET /api/systemic/network         → Full contagion network summary
    GET /api/systemic/propagators     → Top-N risk propagators
    GET /api/systemic/{ticker}        → Per-ticker systemic exposure

Author: samvo
Version: 2.1 (+ Systemic Contagion)
"""

from fastapi import APIRouter, Query, Request, HTTPException, status
from src.api.dependencies import limiter
from src.modules.credit_risk.service import CreditRiskService

router = APIRouter(tags=["credit"])


@router.get("/api/credit-health/{ticker}")
def get_corporate_credit_health(ticker: str):
    """
    Retrieve deep fundamental credit indicators and XGBoost bankruptcy alert ratings.
    Delegates all heavy lifting to CreditRiskService.
    """
    try:
        return CreditRiskService.get_credit_health(ticker)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Credit health service temporarily unavailable: {str(e)}"
        )


@router.get("/api/credit-risk/scan")
@limiter.limit("10/minute")
def scan_credit_risk(
    request: Request,
    tickers: str = Query(..., description="Danh sách các mã cách nhau bằng dấu phẩy"),
    limit: int = Query(default=50, ge=1, le=100)
):
    """
    Batch scan multiple tickers for credit health. Max 50 tickers.
    """
    ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]
    if len(ticker_list) > 50:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Quá giới hạn 50 mã chứng khoán cho mỗi lượt quét."
        )
    return CreditRiskService.scan_tickers(ticker_list, limit=limit)



# ── Systemic / Contagion Risk ─────────────────────────────────────────────────

@router.get("/api/systemic/network")
def get_systemic_network():
    """
    Build (or return cached) the Vietnamese stock market contagion network.

    Returns graph-level statistics and top-10 risk propagators / most-vulnerable nodes.
    Note: First call may take 20-40s while the NetworkX graph is constructed.
    Subsequent calls within 30 minutes return from cache.
    """
    from src.modules.credit_risk.systemic.systemic_service import SystemicRiskService
    return SystemicRiskService.get_network_summary()


@router.get("/api/systemic/propagators")
def get_top_propagators(
    n: int = Query(default=10, ge=1, le=50, description="Số lượng propagators trả về"),
):
    """
    Return the top-N most systemically important tickers ranked by outbound
    contagion influence in the Vietnamese equity market.
    """
    from src.modules.credit_risk.systemic.systemic_service import SystemicRiskService
    return {
        "status": "ok",
        "count": n,
        "propagators": SystemicRiskService.get_top_propagators(n),
    }


@router.get("/api/systemic/{ticker}")
def get_ticker_systemic_profile(ticker: str):
    """
    Contagion profile for a single ticker — outbound influence (who it can shock)
    and inbound exposure (who can shock it), plus systemic importance label.
    """
    from src.modules.credit_risk.systemic.systemic_service import SystemicRiskService
    return SystemicRiskService.get_ticker_contagion(ticker)
