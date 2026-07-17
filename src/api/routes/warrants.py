# -*- coding: utf-8 -*-
"""
🏆 FINVISTA: WARRANT ROUTES (DELIVERY LAYER)
===========================================
FastAPI routes for Covered Warrant pricing, scanning, and simulations.
Strictly handles HTTP request/response, delegating all logic to WarrantService.

Author: samvo
Version: 2.0 (Clean Architecture Refactored)
"""

import asyncio
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from src.api import state
from src.api.dependencies import limiter
from src.api.websocket import manager
from src.modules.cw_pricing.service import WarrantService
from src.modules.trading_engine.ai_committee_service import AICommitteeService

router = APIRouter(tags=["warrants"])
ai_committee = AICommitteeService()


class GreeksCalculatorRequest(BaseModel):
    underlying_price: float = Field(
        ..., description="Current market price of the underlying asset (VND)", example=28500.0
    )
    strike_price: float = Field(
        ..., description="Strike price of the covered warrant (VND)", example=25000.0
    )
    days_to_maturity: int = Field(
        ..., description="Number of calendar days remaining until expiry", example=95
    )
    implied_volatility: float = Field(
        ...,
        description="Annualized implied volatility (as decimal, e.g. 0.45 for 45%)",
        example=0.42,
    )
    conversion_ratio: float = Field(
        1.0, description="Conversion ratio (e.g. 10.0 for 10:1 ratio)", example=10.0
    )
    risk_free_rate: Optional[float] = Field(
        None,
        description="Continuous risk-free rate (optional, falls back to live 1Y Gov Yield)",
        example=0.045,
    )


class GreekCalculatorResponse(BaseModel):
    delta: float = Field(..., description="Warrant Delta adjusted for conversion ratio")
    gamma: float = Field(..., description="Warrant Gamma adjusted for conversion ratio")
    vega: float = Field(..., description="Warrant Vega adjusted for conversion ratio")
    theta: float = Field(..., description="Warrant Theta per calendar day (VND)")
    rho: float = Field(..., description="Warrant Rho")
    moneyness: float = Field(..., description="Underlying / Strike")
    moneyness_category: str = Field(..., description="ITM, ATM, or OTM")
    prob_itm: float = Field(..., description="Probability of expiring in-the-money")


@router.get("/api/warrants/opportunities")
def get_cw_opportunities(
    strategy: str = Query(
        "balanced", pattern="^(balanced|safe|aggressive)$", description="Target trading profile"
    ),
    underlying: Optional[str] = Query(
        None, description="Filter by underlying stock ticker (e.g. HPG)"
    ),
    limit: int = Query(10, ge=1, le=1000, description="Max recommendations to return"),
    force_refresh: bool = Query(
        False, description="Force running full market crawl and calculations"
    ),
):
    """
    Retrieve elite quantitative Covered Warrant recommendations sorted by G-Score.
    Delegates retrieval and refresh logic to WarrantService.
    """
    return WarrantService.get_opportunities(
        strategy=strategy,
        underlying=underlying,
        limit=limit,
        force_refresh=force_refresh
    )


@router.get("/api/warrants/news")
def get_corporate_news(
    symbol: Optional[str] = Query(None, description="Filter by warrant symbol or stock ticker"),
    category: Optional[str] = Query(None, description="Filter by category (e.g. 'Cổ phiếu cơ sở')"),
    limit: int = Query(20, ge=1, le=100),
):
    """
    Retrieve latest corporate news and warrant-specific announcements.
    """
    return WarrantService.get_news(symbol=symbol, category=category, limit=limit)


@router.get("/api/warrants/events")
def get_corporate_events(
    ticker: Optional[str] = Query(None, description="Filter by underlying stock ticker"),
    limit: int = Query(20, ge=1, le=100),
):
    """
    Retrieve upcoming corporate events and dividend schedules for underlying stocks.
    """
    return WarrantService.get_events(ticker=ticker, limit=limit)


@router.post("/api/warrants/greeks", response_model=GreekCalculatorResponse)
def calculate_greeks(req: GreeksCalculatorRequest):
    """
    Dynamic BSM Options Solver Calculator. Accepts price, strike, volatility
    and returns full Greeks and ITM probabilities via WarrantService.
    """
    return WarrantService.calculate_greeks(
        underlying_price=req.underlying_price,
        strike_price=req.strike_price,
        days_to_maturity=req.days_to_maturity,
        implied_volatility=req.implied_volatility,
        conversion_ratio=req.conversion_ratio,
        risk_free_rate=req.risk_free_rate
    )


@router.post("/api/warrants/scan")
@limiter.limit("1/minute")
async def trigger_market_scan(
    request: Request,
    strategy: str = Query("balanced", pattern="^(balanced|safe|aggressive)$"),
):
    """
    Manually trigger a complete real-time market data crawl and quantitative analysis scan.
    Rate limited to 1 execution per minute per client IP. Broadcasts completion state to WebSockets.
    """
    try:
        from src.modules.cw_pricing.backtest.run_analysis import run_quant_pipeline_programmatic
        print("⚡ Manual trigger: Real-time quantitative scanner initiated...")
        
        # We still run this directly here to manage the state and websocket broadcast
        # but the core logic is in run_quant_pipeline_programmatic
        df = await asyncio.to_thread(run_quant_pipeline_programmatic, strategy=strategy)
        
        state.pipeline_cache["data"] = df
        state.pipeline_cache["last_scanned"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        await manager.broadcast({
            "event": "market_scan_completed",
            "message": (
                f"Real-time quantitative scan successfully completed! "
                f"Refreshed {len(df)} Covered Warrants."
            ),
            "timestamp": state.pipeline_cache["last_scanned"],
        })

        return {
            "status": "success",
            "message": (
                f"Successfully completed real-time quant scanner! Refreshed {len(df)} warrants."
            ),
            "last_updated": state.pipeline_cache["last_scanned"],
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Scanner execution failed: {str(e)}",
        )


async def run_async_scan_task(strategy: str):
    """Worker function to run heavy quant calculations in a worker thread and broadcast over WS."""
    try:
        from src.modules.cw_pricing.backtest.run_analysis import run_quant_pipeline_programmatic
        print(f"⚙️ [Async Background Task] Starting full quant scan under strategy: {strategy}")
        await asyncio.to_thread(run_quant_pipeline_programmatic, strategy=strategy)
        print("✅ [Async Background Task] Successfully completed scan and synchronized to database.")

        await manager.broadcast({
            "event": "market_scan_completed",
            "message": (
                "Background market data scan finished and SQLite DB is fully synchronized."
            ),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })
    except Exception as e:
        print(f"❌ [Async Background Task] Scan failed: {e}")


@router.post("/api/warrants/scan/async", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("1/minute")
async def trigger_market_scan_async(
    request: Request,
    background_tasks: BackgroundTasks,
    strategy: str = Query("balanced", pattern="^(balanced|safe|aggressive)$"),
):
    """
    Asynchronously triggers a complete real-time market data crawl and quantitative scan.
    """
    background_tasks.add_task(run_async_scan_task, strategy)

    await manager.broadcast({
        "event": "market_scan_queued",
        "message": (
            f"Market scan asynchronously queued in background under strategy: '{strategy}'"
        ),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })

    return {
        "status": "accepted",
        "message": (
            "Market scan successfully queued in background task queue. "
            "Check logs or query database."
        ),
        "strategy_queued": strategy,
    }


@router.get("/api/warrants/{symbol}/simulate")
def get_warrant_simulation(symbol: str):
    """
    Generate a 2D P/L Scenario Matrix for a specific Covered Warrant.
    Delegates complex simulation logic to WarrantService.
    """
    return WarrantService.simulate_scenarios(symbol)


@router.get("/api/warrants/{symbol}/history")
def get_warrant_history(
    symbol: str,
    days: int = Query(15, ge=5, le=1000, description="Number of trading sessions to look back"),
):
    """
    Retrieve historical volatility structures and Greeks via WarrantService.
    """
    return WarrantService.get_history(symbol=symbol, days=days)


@router.post("/api/warrants/{symbol}/deep-analysis")
async def get_warrant_deep_analysis(symbol: str):
    """
    Execute the full 7-layer AI Quant Committee analysis for a specific warrant.
    Includes Quant checks, Credit (XGBoost), Macro, Vision, Options Deep Dive, and AI Debate.
    """
    try:
        result = await ai_committee.analyze_opportunity(symbol)
        if result.get("status") == "rejected":
            return result
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Deep Analysis failed: {str(e)}",
        )
