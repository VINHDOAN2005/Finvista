# -*- coding: utf-8 -*-
"""
Bước 1 — Dual-Layer Exposure Assessment (CPCS + CW basket).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.core.utils import logger
from src.modules.news_impact.utils import (
    classify_news_type,
    compute_pre_positioning,
    load_hv_cache,
    summarize_cw_basket,
)


def assess_single_event_exposure(
    event: dict,
    prices_map: dict,
    basket: List[dict],
    gex_stats: Optional[dict] = None,
) -> Dict[str, Any]:
    """Structured B1 output for one aligned news event."""
    sym = event["symbol"]
    df_prices = prices_map.get(sym)
    pre_pos = compute_pre_positioning(df_prices, event["aligned_date"])
    basket_summary = summarize_cw_basket(basket)
    hv = load_hv_cache(sym)

    news_type = classify_news_type(event.get("title", ""), event.get("category", ""))
    credibility = "HIGH" if news_type == "OFFICIAL" else "MEDIUM" if news_type == "CORRIDOR" else "LOW"

    gex_total = None
    mm_pressure = "UNKNOWN"
    if gex_stats and "total_gex" in gex_stats:
        gex_total = gex_stats["total_gex"]
        mm_pressure = "STABLE_DAMPENER" if gex_total > 0 else "VOL_ACCELERATOR"

    return {
        "event_id": event["id"],
        "underlying": sym,
        "title": event.get("title"),
        "aligned_date": str(event["aligned_date"]),
        "sentiment": event.get("sentiment"),
        "cpcs_exposure": {
            "news_type": news_type,
            "credibility": credibility,
            "category": event.get("category"),
            "pre_positioning": pre_pos,
            "hv_annualized": hv,
            "buy_rumor_risk": pre_pos.get("buy_rumor_risk", False),
        },
        "cw_exposure": {
            "basket": basket,
            "summary": basket_summary,
            "iv_crush_risk": basket_summary.get("iv_crush_risk"),
        },
        "mm_context": {
            "total_gex": gex_total,
            "mm_pressure": mm_pressure,
        },
    }


def assess_portfolio_exposure(
    aligned_events: List[dict],
    prices_map: dict,
    baskets: Dict[str, list],
    include_gex: bool = True,
) -> List[Dict[str, Any]]:
    """Run exposure assessment for all aligned events."""
    logger.info("🎬 [Exposure] Dual-layer exposure assessment (CPCS + CW)...")

    gex_cache: Dict[str, dict] = {}
    if include_gex:
        try:
            from src.modules.cw_pricing.models.gex_engine import calculate_aggregate_gex

            for sym in baskets:
                try:
                    gex_cache[sym] = calculate_aggregate_gex(sym)
                except Exception as e:
                    logger.debug(f"GEX skip {sym}: {e}")
        except ImportError:
            pass

    results = []
    for ev in aligned_events:
        sym = ev["symbol"]
        exposure = assess_single_event_exposure(
            ev,
            prices_map,
            baskets.get(sym, []),
            gex_stats=gex_cache.get(sym),
        )
        results.append(exposure)

    logger.info(f"✅ [Exposure] Assessed {len(results)} events.")
    return results
