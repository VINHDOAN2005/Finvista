# -*- coding: utf-8 -*-
"""
🏆 FINVISTA: PORTFOLIO ROUTES (DELIVERY LAYER)
=============================================
FastAPI routes for paper trading portfolio management.
Delegates all business logic and persistence to PortfolioService.

Author: samvo
Version: 2.0 (Clean Architecture Refactored)
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from src.api.dependencies import get_current_user
from src.api.websocket import manager
from src.modules.trading_engine.portfolio_service import PortfolioService

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


class OrderRequest(BaseModel):
    symbol: str = Field(..., description="Covered warrant symbol, e.g. CACB2510", example="CACB2510")
    side: str = Field(
        ..., description="BUY or SELL", pattern="^(BUY|SELL|buy|sell)$", example="BUY"
    )
    qty: Optional[int] = Field(
        None,
        description=(
            "Quantity to buy/sell. If BUY, qty is optional (allocates max 20% NAV by default "
            "if not specified). Must be multiple of 100."
        ),
    )
    price: Optional[float] = Field(
        None, description="Optional override price. If not specified, uses current live market price."
    )
    reason: Optional[str] = Field("Manual User Order", description="Optional reason for the transaction")


@router.get("")
def get_portfolio(current_user: dict = Depends(get_current_user)):
    """
    Retrieve detailed Paper Trading portfolio state.
    Delegates to PortfolioService for SQLite-based data retrieval.
    """
    return PortfolioService.get_portfolio(username=current_user["username"])


@router.post("/orders")
async def place_order(req: OrderRequest, current_user: dict = Depends(get_current_user)):
    """
    Place a paper trading order.
    Delegates validation and execution to PortfolioService.
    Broadcasts successful transactions over WebSocket.
    """
    res = PortfolioService.place_order(
        username=current_user["username"],
        symbol=req.symbol,
        side=req.side,
        qty=req.qty,
        price_override=req.price,
        reason=req.reason
    )
    
    if res.get("status") == "success":
        from datetime import datetime
        await manager.broadcast({
            "event": "order_executed",
            "username": current_user["username"],
            "message": res.get("message"),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })
        return res
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=res.get("message"))


@router.post("/reset")
def reset_trading_portfolio(current_user: dict = Depends(get_current_user)):
    """
    Reset paper trading account to initial balance.
    """
    return PortfolioService.reset_portfolio(username=current_user["username"])


@router.post("/scan")
def trigger_paper_trader_scan(
    force: bool = Query(False, description="Set to true to bypass HOSE trading hours checks"),
    current_user: dict = Depends(get_current_user),
):
    """
    Trigger automated risk-management scan via PortfolioService.
    """
    actions = PortfolioService.scan_and_trade(username=current_user["username"], force=force)
    return {
        "status": "success",
        "actions_executed": actions,
    }
