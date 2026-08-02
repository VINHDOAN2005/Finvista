# -*- coding: utf-8 -*-
"""
FINVISTA: Complete Dual-Layer News Impact Pipeline Orchestrator
===============================================================
Steps 1–6: CPCS event study (existing)
Steps 7–8: CW basket exposure + CAR
Exposure / Forecast / Reality: B1 → B2 → B3 framework
Step 9: Consolidated reporting
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.core.database import SessionLocal
from src.core.utils import logger

from src.modules.news_impact.news_step1_prepare import prepare_news_events
from src.modules.news_impact.news_step2_align import align_events_to_prices
from src.modules.news_impact.news_step3_calculate import calculate_forward_returns
from src.modules.news_impact.news_step4_test import perform_significance_tests
from src.modules.news_impact.news_step5_report import print_impact_report
from src.modules.news_impact.news_step6_train_ml import train_news_ml_model
from src.modules.news_impact.news_step7_cw_basket import build_cw_basket_map
from src.modules.news_impact.news_step8_cw_car import calculate_cw_event_returns
from src.modules.news_impact.news_step9_dual_report import (
    build_summary_payload,
    print_dual_layer_report,
)
from src.modules.news_impact.exposure_assessor import assess_portfolio_exposure
from src.modules.news_impact.forecast_engine import build_forecasts
from src.modules.news_impact.reality_checker import run_reality_checks


def run_full_pipeline(
    symbol: str = None,
    keyword: str = None,
    event_date: str = None,
    min_events: int = 3,
    horizons: Optional[List[int]] = None,
    train_ml: bool = False,
    skip_report: bool = False,
    include_gex: bool = True,
) -> Dict[str, Any]:
    """
    Run the complete dual-layer news impact pipeline.

    Args:
        symbol:      Underlying ticker filter (e.g. VHM)
        keyword:     Title/summary keyword filter
        event_date:  YYYY-MM-DD — focus forecast/reality on this event date
        min_events:  Minimum news events required
        horizons:    Forward return horizons (default [1,3,5,10,20])
        train_ml:    Train/update ML model after pipeline
        skip_report: Skip stdout reports
        include_gex: Include GEX in exposure assessment

    Returns:
        Full pipeline result dict (API-ready)
    """
    horizons = horizons or [1, 3, 5, 10, 20]
    db = SessionLocal()
    empty = {"status": "failed", "reason": "insufficient_data"}

    try:
        # ── Step 1: Prepare events ──
        df_events = prepare_news_events(db, symbol=symbol, keyword=keyword)
        if df_events.empty or len(df_events) < min_events:
            logger.warning(
                f"Pipeline aborted: need >={min_events} events, found {len(df_events)}"
            )
            return {**empty, "events_found": len(df_events)}

        # ── Step 2: Align to trading sessions ──
        alignment = align_events_to_prices(db, df_events)
        aligned_events = alignment["aligned_events"]
        prices_map = alignment["prices_map"]
        market_returns = alignment["market_returns"]

        if not aligned_events:
            return {**empty, "reason": "alignment_failed"}

        if event_date:
            prefix = event_date[:10]
            filtered = [
                e for e in aligned_events
                if str(e["aligned_date"]).startswith(prefix)
            ]
            if filtered:
                aligned_events = filtered
                logger.info(f"📅 Event-date filter {prefix}: {len(aligned_events)} events")
            else:
                logger.warning(f"No events aligned on {prefix}; using all aligned events")

        # ── Step 3: CPCS forward returns / CAR ──
        calc = calculate_forward_returns(
            aligned_events, prices_map, market_returns, horizons=horizons
        )
        df_returns = calc["event_returns"]
        horizon_stats = calc["horizon_stats"]

        if not horizon_stats:
            return {**empty, "reason": "car_calculation_failed"}

        # ── Step 4: Statistical significance ──
        horizon_stats = perform_significance_tests(
            df_returns, prices_map, market_returns, horizon_stats, horizons=horizons
        )

        # ── Step 7: CW basket map ──
        basket_data = build_cw_basket_map(db, aligned_events)
        baskets = basket_data["baskets"]

        # ── Step 8: CW CAR around same events ──
        cw_calc = calculate_cw_event_returns(
            db, aligned_events, baskets, market_returns, horizons=horizons
        )
        cw_horizon_stats = cw_calc["cw_horizon_stats"]
        cw_prices_map = cw_calc["cw_prices_map"]

        # ── B1: Exposure assessment ──
        exposures = assess_portfolio_exposure(
            aligned_events,
            prices_map,
            baskets,
            include_gex=include_gex and bool(event_date),
        )

        # ── B2: Ex-ante forecasts ──
        forecasts = build_forecasts(
            exposures, horizon_stats, horizons=[1, 3, 5], event_date=event_date
        )

        # ── B3: Reality check ──
        reality_checks = run_reality_checks(
            forecasts,
            exposures,
            prices_map,
            cw_prices_map,
            market_returns,
            horizon_stats,
            horizons=[1, 3, 5],
        )

        # ── Step 6: Optional ML training ──
        ml_metrics = {}
        if train_ml:
            ml_metrics = train_news_ml_model(
                df_returns, prices_map, market_returns, horizon_target=5
            )

        # ── Reports ──
        if not skip_report:
            print_impact_report(symbol, keyword, horizon_stats)
            print_dual_layer_report(
                symbol, horizon_stats, cw_horizon_stats,
                exposures, forecasts, reality_checks,
            )

        summary = build_summary_payload(
            symbol,
            horizon_stats,
            cw_horizon_stats,
            exposures,
            forecasts,
            reality_checks,
            news_count=len(df_events),
        )

        return {
            "status": "ok",
            "mode": "full_dual_layer",
            "symbol": (symbol or "").upper() or None,
            "event_date_filter": event_date,
            "events_aligned": len(aligned_events),
            "horizon_stats": horizon_stats,
            "cw_horizon_stats": cw_horizon_stats,
            "cw_basket_summaries": basket_data["summaries"],
            "event_returns": df_returns.to_dict(orient="records"),
            "cw_event_returns": cw_calc["cw_event_returns"].to_dict(orient="records"),
            "exposures": exposures,
            "forecasts": forecasts,
            "reality_checks": reality_checks,
            "ml_metrics": ml_metrics or None,
            "summary": summary,
        }

    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        return {"status": "error", "reason": str(e)}
    finally:
        db.close()


def run_event_study(
    symbol: str,
    event_date: str,
    keyword: str = None,
    horizons: Optional[List[int]] = None,
) -> Dict[str, Any]:
    """
    Single-event case study (e.g. VHM ĐHCĐ 2026-04-21).
    Runs full pipeline with min_events=1 and event_date filter.
    """
    return run_full_pipeline(
        symbol=symbol,
        keyword=keyword,
        event_date=event_date,
        min_events=1,
        horizons=horizons or [1, 3, 5, 10],
        train_ml=False,
        include_gex=True,
    )
