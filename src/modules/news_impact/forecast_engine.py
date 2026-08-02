# -*- coding: utf-8 -*-
"""
Bước 2 — Ex-ante forecast engine (CPCS CAR scenarios + CW Delta/Vega paths).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from src.core.utils import logger
from src.modules.news_impact.utils import safe_pct


def _historical_car_prior(horizon_stats: dict, horizon: int, sentiment: str) -> Optional[float]:
    if horizon not in horizon_stats:
        return None
    sent_stats = horizon_stats[horizon].get("sentiment_stats", {})
    if sentiment in sent_stats:
        return float(sent_stats[sentiment].get("mean_car", 0.0))
    return float(horizon_stats[horizon].get("mean_car", 0.0))


def _pick_primary_scenario(buy_rumor_risk: bool, sentiment: str) -> str:
    if buy_rumor_risk and sentiment == "POSITIVE":
        return "B_SELL_THE_NEWS"
    if sentiment == "NEGATIVE":
        return "C_DOWNSIDE"
    return "A_CONTINUATION"


def forecast_cw_move(
    cw: dict,
    spot_change_pct: float,
    iv_change_pts: float,
    days: int = 1,
) -> float:
    """Approximate CW % change: delta leg + vega leg + theta leg."""
    delta = float(cw.get("delta") or 0.0)
    vega = float(cw.get("vega") or 0.0)
    theta = float(cw.get("theta") or 0.0)
    gearing = float(cw.get("gearing") or 0.0)
    price = float(cw.get("price") or 0.0)

    if price <= 0 and gearing > 0:
        delta_pct = spot_change_pct * gearing / 100.0
    else:
        delta_pct = (delta * spot_change_pct / 100.0) if delta else spot_change_pct * gearing / 100.0

    vega_pct = (vega * iv_change_pts / price) if price > 0 and vega else 0.0
    theta_pct = (theta * days / price) if price > 0 and theta else 0.0
    return (delta_pct + vega_pct + theta_pct) * 100.0


def build_event_forecast(
    exposure: dict,
    horizon_stats: dict,
    horizons: List[int] = None,
) -> Dict[str, Any]:
    """Generate A/B/C scenarios for one event."""
    horizons = horizons or [1, 3, 5]
    cpcs = exposure["cpcs_exposure"]
    cw_summary = exposure["cw_exposure"]["summary"]
    sentiment = exposure.get("sentiment", "NEUTRAL")
    buy_rumor = cpcs.get("buy_rumor_risk", False)
    primary = _pick_primary_scenario(buy_rumor, sentiment)

    scenario_defs = {
        "A_CONTINUATION": {"spot": [0.03, 0.05, 0.04], "iv": [-1, -2, -3]},
        "B_SELL_THE_NEWS": {"spot": [0.05, 0.01, -0.03], "iv": [-3, -5, -4]},
        "C_DOWNSIDE": {"spot": [-0.02, -0.04, -0.05], "iv": [3, 2, 0]},
    }

    cpcs_forecast = {}
    for i, h in enumerate(horizons):
        prior = _historical_car_prior(horizon_stats, h, sentiment) or 0.0
        adj = -0.02 if buy_rumor and sentiment == "POSITIVE" else 0.0
        for name, spec in scenario_defs.items():
            spot_h = spec["spot"][min(i, len(spec["spot"]) - 1)]
            cpcs_forecast.setdefault(name, {})[h] = {
                "expected_car_pct": safe_pct(prior + adj + spot_h * 0.5),
                "spot_change_pct": safe_pct(spot_h),
            }

    cw_forecast = {}
    basket = exposure["cw_exposure"].get("basket", [])
    iv_crush = cw_summary.get("iv_crush_risk") == "HIGH"

    for name, spec in scenario_defs.items():
        iv_pts = spec["iv"]
        if iv_crush and name == "B_SELL_THE_NEWS":
            iv_pts = [x - 2 for x in iv_pts]

        cw_by_symbol = {}
        for cw in basket[:5]:
            sym = cw["cw_symbol"]
            cw_by_symbol[sym] = {
                "issuer_tier": cw.get("issuer_tier"),
                "gearing": cw.get("gearing"),
                "horizons": {},
            }
            for i, h in enumerate(horizons):
                spot_h = spec["spot"][min(i, len(spec["spot"]) - 1)]
                iv_h = iv_pts[min(i, len(iv_pts) - 1)]
                cw_by_symbol[sym]["horizons"][h] = {
                    "expected_pct": round(
                        forecast_cw_move(cw, spot_h * 100, iv_h, days=h), 2
                    ),
                    "iv_change_pts": iv_h,
                }
        cw_forecast[name] = cw_by_symbol

    return {
        "event_id": exposure["event_id"],
        "underlying": exposure["underlying"],
        "aligned_date": exposure["aligned_date"],
        "primary_scenario": primary,
        "scenarios": list(scenario_defs.keys()),
        "cpcs_forecast": cpcs_forecast,
        "cw_forecast": cw_forecast,
        "duration_hint": "1-2 sessions" if buy_rumor else "3-10 sessions",
        "generated_at": datetime.now().isoformat(),
    }


def build_forecasts(
    exposures: List[dict],
    horizon_stats: dict,
    horizons: List[int] = None,
    event_date: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Build forecasts for all events; optionally filter to one event date."""
    logger.info("🎬 [Forecast] Generating dual-layer ex-ante scenarios...")
    forecasts = []
    for exp in exposures:
        if event_date and not str(exp["aligned_date"]).startswith(event_date[:10]):
            continue
        forecasts.append(build_event_forecast(exp, horizon_stats, horizons=horizons))

    logger.info(f"✅ [Forecast] Generated {len(forecasts)} event forecasts.")
    return forecasts
