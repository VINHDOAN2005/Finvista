# -*- coding: utf-8 -*-
"""
Bước 3 — Reality check: compare ex-ante forecast vs actual CPCS + CW moves.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np

from src.core.utils import logger
from src.modules.news_impact.utils import safe_pct


def _actual_return(prices_map: dict, symbol: str, aligned_date, horizon: int) -> Optional[float]:
    df = prices_map.get(symbol)
    if df is None or df.empty:
        return None

    match = df[df["date"] == aligned_date]
    if match.empty:
        return None

    idx_0 = match.index[0]
    ref = float(df.iloc[idx_0 - 1]["close"]) if idx_0 > 0 else float(df.iloc[idx_0]["open"])
    idx_h = idx_0 + horizon - 1
    if ref <= 0 or idx_h >= len(df):
        return None

    return (float(df.iloc[idx_h]["close"]) - ref) / ref


def check_single_forecast(
    forecast: dict,
    exposure: dict,
    prices_map: dict,
    cw_prices_map: dict,
    market_returns: dict,
    horizon_stats: dict,
    horizons: List[int] = None,
) -> Dict[str, Any]:
    """Compare primary scenario forecast against realized returns."""
    horizons = horizons or [1, 3, 5]
    underlying = forecast["underlying"]
    aligned_date = exposure["aligned_date"]
    primary = forecast["primary_scenario"]
    sentiment = exposure.get("sentiment", "NEUTRAL")

    cpcs_actual = {}
    cpcs_slippage = {}
    for h in horizons:
        raw = _actual_return(prices_map, underlying, aligned_date, h)
        if raw is None:
            continue

        comp_mkt = 1.0
        df = prices_map[underlying]
        match = df[df["date"] == aligned_date]
        if not match.empty:
            idx_0 = match.index[0]
            for offset in range(h):
                i_curr = idx_0 + offset
                if i_curr < len(df):
                    comp_mkt *= 1.0 + market_returns.get(df.iloc[i_curr]["date"], 0.0)
        car = raw - (comp_mkt - 1.0)

        expected = forecast["cpcs_forecast"].get(primary, {}).get(h, {})
        exp_car = (expected.get("expected_car_pct") or 0.0) / 100.0

        cpcs_actual[h] = {"raw_pct": safe_pct(raw), "car_pct": safe_pct(car)}
        cpcs_slippage[h] = {
            "car_error_pct": safe_pct(car - exp_car),
            "direction_match": (car >= 0) == (exp_car >= 0),
        }

    cw_actual = {}
    cw_slippage = {}
    for cw in exposure["cw_exposure"].get("basket", [])[:5]:
        sym = cw["cw_symbol"]
        cw_actual[sym] = {}
        cw_slippage[sym] = {}
        for h in horizons:
            raw = _actual_return(cw_prices_map, sym, aligned_date, h)
            if raw is None:
                continue
            exp = (
                forecast.get("cw_forecast", {})
                .get(primary, {})
                .get(sym, {})
                .get("horizons", {})
                .get(h, {})
            )
            exp_pct = (exp.get("expected_pct") or 0.0) / 100.0
            cw_actual[sym][h] = {"raw_pct": safe_pct(raw)}
            cw_slippage[sym][h] = {
                "error_pct": safe_pct(raw - exp_pct),
                "direction_match": (raw >= 0) == (exp_pct >= 0),
            }

    verdict = _compute_verdict(cpcs_slippage, exposure, primary)

    return {
        "event_id": forecast["event_id"],
        "underlying": underlying,
        "aligned_date": str(aligned_date),
        "primary_scenario": primary,
        "cpcs_actual": cpcs_actual,
        "cpcs_slippage": cpcs_slippage,
        "cw_actual": cw_actual,
        "cw_slippage": cw_slippage,
        "verdict": verdict,
        "historical_prior_h1": safe_pct(
            horizon_stats.get(1, {}).get("sentiment_stats", {}).get(sentiment, {}).get("mean_car")
        ),
    }


def _compute_verdict(cpcs_slippage: dict, exposure: dict, primary: str) -> str:
    if not cpcs_slippage:
        return "INSUFFICIENT_DATA"

    h1 = cpcs_slippage.get(1) or cpcs_slippage.get(min(cpcs_slippage.keys()))
    if not h1:
        return "INSUFFICIENT_DATA"

    if h1.get("direction_match"):
        return "MATCH"

    buy_rumor = exposure["cpcs_exposure"].get("buy_rumor_risk")
    if buy_rumor and primary == "B_SELL_THE_NEWS" and not h1.get("direction_match"):
        return "INVERTED_SELL_NEWS"
    return "PARTIAL_MISS"


def run_reality_checks(
    forecasts: List[dict],
    exposures: List[dict],
    prices_map: dict,
    cw_prices_map: dict,
    market_returns: dict,
    horizon_stats: dict,
    horizons: List[int] = None,
) -> List[Dict[str, Any]]:
    logger.info("🎬 [Reality Check] Comparing forecasts vs actual price paths...")
    exp_by_id = {e["event_id"]: e for e in exposures}
    results = []

    for fc in forecasts:
        exp = exp_by_id.get(fc["event_id"])
        if not exp:
            continue
        results.append(
            check_single_forecast(
                fc, exp, prices_map, cw_prices_map, market_returns, horizon_stats, horizons
            )
        )

    logger.info(f"✅ [Reality Check] Completed {len(results)} slippage analyses.")
    return results
