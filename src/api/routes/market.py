# -*- coding: utf-8 -*-
"""
🏆 FINVISTA: MARKET DATA ROUTES
================================
FastAPI routes for market metadata and underlying stock data.
"""

from fastapi import APIRouter, Query, BackgroundTasks
from src.modules.cw_pricing.service import WarrantService

router = APIRouter(tags=["market"])


def run_news_scraper_bg():
    try:
        from src.modules.credit_risk.etl.vietstock_scraper import VietstockScraper
        scraper = VietstockScraper()
        # Fetch news for the top 10 underlyings to be fast and avoid rate-limiting
        scraper.run(limit=10)
    except Exception as e:
        import logging
        logging.error(f"Error running background news scraper: {e}")


@router.get("/api/market/metadata")
def get_market_metadata(force_refresh: bool = Query(False)):
    """
    Retrieve market metadata including available underlyings, sectors, and market status.
    """
    try:
        # Get cached market data from WarrantService
        metadata = WarrantService.get_market_metadata(force_refresh=force_refresh)
        return metadata
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to retrieve market metadata: {str(e)}"
        }


@router.get("/api/market/underlyings")
def get_underlyings(
    background_tasks: BackgroundTasks,
    news_limit: int = Query(20, ge=1, le=100),
    language: str = Query("en"),
    force_refresh: bool = Query(False)
):
    """
    Retrieve underlying stock data with optional news information.
    """
    if force_refresh:
        background_tasks.add_task(run_news_scraper_bg)
    try:
        data = WarrantService.get_underlyings(
            news_limit=news_limit,
            language=language,
            force_refresh=force_refresh
        )
        return data
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to retrieve underlyings: {str(e)}",
            "underlyings": []
        }
