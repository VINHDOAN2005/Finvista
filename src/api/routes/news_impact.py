# -*- coding: utf-8 -*-
"""
FINVISTA: NEWS IMPACT ROUTES — dual-layer pipeline API
"""

from fastapi import APIRouter, Query
from src.modules.news_impact.service import NewsImpactService

router = APIRouter(tags=["news-impact"])


@router.get("/api/news-impact/{ticker}")
def get_news_impact(
    ticker: str,
    days: int = Query(default=90, ge=7, le=365),
    full_pipeline: bool = Query(default=False, description="Chạy pipeline CAR + CW (nặng hơn)"),
):
    return NewsImpactService.get_news_impact(
        ticker=ticker, days=days, run_pipeline=full_pipeline
    )


@router.get("/api/news-impact/{ticker}/pipeline")
def run_pipeline(
    ticker: str,
    event_date: str = Query(default=None, description="YYYY-MM-DD — lọc case study"),
    keyword: str = Query(default=None),
    train_ml: bool = Query(default=False),
):
    """Chạy full dual-layer pipeline B1→B2→B3 cho một mã CPCS."""
    if event_date:
        return NewsImpactService.run_event_study(
            symbol=ticker, event_date=event_date, keyword=keyword
        )
    return NewsImpactService.run_full_pipeline(
        symbol=ticker, keyword=keyword, min_events=1, train_ml=train_ml, skip_report=True
    )


@router.get("/api/news-impact/{ticker}/ml-signal")
def get_news_ml_signal(ticker: str):
    return NewsImpactService.get_ml_signal(ticker=ticker)


@router.get("/api/news-impact/{ticker}/sentiment")
def get_news_sentiment_score(
    ticker: str,
    days: int = Query(default=30, ge=7, le=180),
):
    score = NewsImpactService.get_ticker_sentiment_score(ticker=ticker, days=days)
    label = "BULLISH" if score > 0.1 else "BEARISH" if score < -0.1 else "NEUTRAL"
    return {
        "ticker": ticker.upper().strip(),
        "period_days": days,
        "sentiment_score": score,
        "sentiment_label": label,
    }
