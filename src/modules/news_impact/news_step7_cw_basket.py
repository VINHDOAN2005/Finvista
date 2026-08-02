# -*- coding: utf-8 -*-
"""
Step 7: Map underlying news events to live CW basket exposure.
"""

from __future__ import annotations

from typing import Any, Dict, List

from sqlalchemy.orm import Session

from src.core.utils import logger
from src.modules.news_impact.utils import load_cw_basket_for_underlying, summarize_cw_basket


def build_cw_basket_map(
    db: Session,
    aligned_events: List[dict],
) -> Dict[str, Any]:
    """
    For each underlying symbol in aligned events, load CW basket metadata.

    Returns:
        {
            "baskets": {underlying: [cw_dict, ...]},
            "summaries": {underlying: summary_dict},
            "event_links": [{event_id, underlying, basket_summary}, ...]
        }
    """
    logger.info("🎬 [Step 7] Building CW basket exposure map for underlyings...")

    underlyings = sorted({ev["symbol"] for ev in aligned_events})
    baskets: Dict[str, list] = {}
    summaries: Dict[str, dict] = {}

    for sym in underlyings:
        basket = load_cw_basket_for_underlying(sym, db_session=db)
        baskets[sym] = basket
        summaries[sym] = summarize_cw_basket(basket)
        logger.info(f"   • {sym}: {summaries[sym]['count']} CW live (avg EG {summaries[sym]['avg_gearing']:.1f}x)")

    event_links = []
    for ev in aligned_events:
        sym = ev["symbol"]
        event_links.append(
            {
                "event_id": ev["id"],
                "underlying": sym,
                "aligned_date": str(ev["aligned_date"]),
                "basket_count": summaries.get(sym, {}).get("count", 0),
                "basket_summary": summaries.get(sym, {}),
            }
        )

    logger.info(f"✅ [Step 7] CW basket map ready for {len(underlyings)} underlyings.")
    return {
        "baskets": baskets,
        "summaries": summaries,
        "event_links": event_links,
    }
