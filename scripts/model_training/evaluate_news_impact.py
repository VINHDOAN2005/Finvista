# -*- coding: utf-8 -*-
"""
FINVISTA: NEWS IMPACT PIPELINE ORCHESTRATOR (CLI entry)
Delegates to src.modules.news_impact.pipeline
"""

import os
import sys
import argparse

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.modules.news_impact.pipeline import run_full_pipeline, run_event_study


def run_news_impact_pipeline(
    symbol: str = None,
    keyword: str = None,
    event_date: str = None,
    min_events: int = 3,
    horizons: list = None,
    train_ml: bool = False,
) -> dict:
    """Backward-compatible wrapper for run.py and scripts."""
    if event_date and symbol:
        return run_event_study(symbol=symbol, event_date=event_date, keyword=keyword)

    return run_full_pipeline(
        symbol=symbol,
        keyword=keyword,
        event_date=event_date,
        min_events=min_events,
        horizons=horizons or [1, 3, 5, 10, 20],
        train_ml=train_ml,
        skip_report=False,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Finvista Dual-Layer News Impact Pipeline")
    parser.add_argument("--symbol", "-s", type=str, help="Ticker (e.g. VHM)")
    parser.add_argument("--keyword", "-k", type=str, help="Filter news by keyword")
    parser.add_argument("--event-date", "-e", type=str, help="Event date YYYY-MM-DD (case study mode)")
    parser.add_argument("--min-events", "-m", type=int, default=3)
    parser.add_argument("--days", "-d", type=str, default="1,3,5,10,20")
    parser.add_argument("--train-ml", action="store_true")

    args = parser.parse_args()
    horizons_list = [int(h.strip()) for h in args.days.split(",") if h.strip().isdigit()]

    run_news_impact_pipeline(
        symbol=args.symbol,
        keyword=args.keyword,
        event_date=args.event_date,
        min_events=args.min_events,
        horizons=horizons_list or [1, 3, 5, 10, 20],
        train_ml=args.train_ml,
    )
