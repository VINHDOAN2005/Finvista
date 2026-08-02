# -*- coding: utf-8 -*-
"""
Step 8: Compute forward returns and CAR for CW basket around CPCS news events.
"""

from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pandas as pd

from src.core.utils import logger
from src.modules.news_impact.news_step2_align import fetch_historical_prices


def calculate_cw_event_returns(
    db,
    aligned_events: List[dict],
    baskets: Dict[str, list],
    market_returns: dict,
    horizons: List[int] = None,
) -> Dict[str, Any]:
    """
    For each CPCS event, compute CW returns on the same aligned trading day.

    Returns:
        {
            "cw_event_returns": DataFrame,
            "cw_horizon_stats": dict,
            "cw_prices_map": dict
        }
    """
    horizons = horizons or [1, 3, 5, 10, 20]
    logger.info("🎬 [Step 8] Calculating CW forward returns aligned to CPCS news events...")

    cw_prices_map: Dict[str, pd.DataFrame] = {}
    rows = []

    for underlying, basket in baskets.items():
        for cw in basket:
            sym = cw["cw_symbol"]
            if sym not in cw_prices_map:
                df = fetch_historical_prices(db, sym)
                if not df.empty:
                    cw_prices_map[sym] = df

    for ev in aligned_events:
        underlying = ev["symbol"]
        basket = baskets.get(underlying, [])
        aligned_date = ev["aligned_date"]

        for cw in basket:
            sym = cw["cw_symbol"]
            if sym not in cw_prices_map:
                continue

            df_prices = cw_prices_map[sym]
            match = df_prices[df_prices["date"] == aligned_date]
            if match.empty:
                continue

            idx_0 = match.index[0]
            ref_price = (
                float(df_prices.iloc[idx_0 - 1]["close"])
                if idx_0 > 0
                else float(df_prices.iloc[idx_0]["open"])
            )
            if ref_price <= 0:
                continue

            row = {
                "event_id": ev["id"],
                "underlying": underlying,
                "cw_symbol": sym,
                "issuer": cw.get("issuer"),
                "issuer_tier": cw.get("issuer_tier"),
                "gearing": cw.get("gearing"),
                "aligned_date": aligned_date,
                "sentiment": ev.get("sentiment"),
                "ref_price": ref_price,
            }

            for h in horizons:
                idx_h = idx_0 + h - 1
                if idx_h < len(df_prices):
                    price_h = float(df_prices.iloc[idx_h]["close"])
                    raw_ret = (price_h - ref_price) / ref_price

                    comp_market_ret = 1.0
                    for offset in range(h):
                        i_curr = idx_0 + offset
                        if i_curr < len(df_prices):
                            curr_date = df_prices.iloc[i_curr]["date"]
                            comp_market_ret *= 1.0 + market_returns.get(curr_date, 0.0)
                    comp_market_ret -= 1.0
                    car_ret = raw_ret - comp_market_ret

                    row[f"return_{h}d"] = raw_ret
                    row[f"car_{h}d"] = car_ret
                else:
                    row[f"return_{h}d"] = np.nan
                    row[f"car_{h}d"] = np.nan

            rows.append(row)

    df_cw = pd.DataFrame(rows)
    cw_horizon_stats = _aggregate_cw_horizon_stats(df_cw, horizons)

    logger.info(f"✅ [Step 8] Computed CW returns for {len(df_cw)} event×CW pairs.")
    return {
        "cw_event_returns": df_cw,
        "cw_horizon_stats": cw_horizon_stats,
        "cw_prices_map": cw_prices_map,
    }


def _aggregate_cw_horizon_stats(df_cw: pd.DataFrame, horizons: List[int]) -> dict:
    stats = {}
    if df_cw.empty:
        return stats

    for h in horizons:
        raw_col = f"return_{h}d"
        car_col = f"car_{h}d"
        if raw_col not in df_cw.columns:
            continue

        valid = df_cw[raw_col].dropna()
        valid_car = df_cw[car_col].dropna()
        if valid.empty:
            continue

        stats[h] = {
            "count": int(len(valid)),
            "mean_raw": float(valid.mean()),
            "mean_car": float(valid_car.mean()) if not valid_car.empty else 0.0,
            "p_up_car": float((valid_car > 0.001).mean()) if not valid_car.empty else 0.0,
            "by_tier": {},
        }

        for tier in df_cw["issuer_tier"].dropna().unique():
            sub = df_cw[df_cw["issuer_tier"] == tier]
            sub_car = sub[car_col].dropna()
            if not sub_car.empty:
                stats[h]["by_tier"][tier] = {
                    "count": int(len(sub_car)),
                    "mean_car": float(sub_car.mean()),
                }

    return stats
