# -*- coding: utf-8 -*-
"""
Step 9: Dual-layer report (CPCS + CW exposure, forecast, reality check).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.core.utils import logger


def print_dual_layer_report(
    symbol: Optional[str],
    horizon_stats: dict,
    cw_horizon_stats: dict,
    exposures: List[dict],
    forecasts: List[dict],
    reality_checks: List[dict],
) -> None:
    """Print consolidated B1 → B2 → B3 report to stdout."""
    sym_str = (symbol or "ALL").upper()
    print("\n" + "=" * 120)
    print("  FINVISTA DUAL-LAYER NEWS IMPACT PIPELINE — CPCS + CW BASKET")
    print("=" * 120)
    print(f"  Mã CPCS: {sym_str}")

    if horizon_stats:
        print("\n── CPCS CAR (Historical Event Study) ──")
        print(f"  {'Horizon':<10} {'N':<6} {'Mean CAR':<12} {'P(up CAR)':<12}")
        for h, st in sorted(horizon_stats.items()):
            print(
                f"  {h}d{'':<8} {st.get('count', 0):<6} "
                f"{st.get('mean_car', 0)*100:>+8.2f}%   {st.get('p_up_car', 0)*100:>8.1f}%"
            )

    if cw_horizon_stats:
        print("\n── CW Basket CAR (Same Events) ──")
        print(f"  {'Horizon':<10} {'N':<6} {'Mean CAR':<12} {'P(up CAR)':<12}")
        for h, st in sorted(cw_horizon_stats.items()):
            print(
                f"  {h}d{'':<8} {st.get('count', 0):<6} "
                f"{st.get('mean_car', 0)*100:>+8.2f}%   {st.get('p_up_car', 0)*100:>8.1f}%"
            )
            for tier, td in st.get("by_tier", {}).items():
                print(f"      └ {tier}: n={td['count']} CAR={td['mean_car']*100:+.2f}%")

    if exposures:
        print("\n── B1: Dual Exposure (latest events, max 5) ──")
        for exp in exposures[-5:]:
            cpcs = exp["cpcs_exposure"]
            cw = exp["cw_exposure"]["summary"]
            pre = cpcs.get("pre_positioning", {}).get("returns", {})
            pre_str = ", ".join(f"{k}={v*100:+.1f}%" for k, v in pre.items()) or "n/a"
            print(f"  [{exp['aligned_date']}] {exp['sentiment']} | {cpcs['news_type']} | pre-run: {pre_str}")
            print(
                f"    CW basket: {cw.get('count', 0)} mã | avg EG {cw.get('avg_gearing', 0):.1f}x | "
                f"IV crush risk: {cw.get('iv_crush_risk')} | buy-rumor: {cpcs.get('buy_rumor_risk')}"
            )
            mm = exp.get("mm_context", {})
            if mm.get("total_gex") is not None:
                print(f"    GEX: {mm['total_gex']:,.0f} → {mm['mm_pressure']}")

    if forecasts:
        print("\n── B2: Ex-ante Forecast (primary scenario) ──")
        for fc in forecasts[:5]:
            primary = fc["primary_scenario"]
            print(f"  [{fc['aligned_date']}] {fc['underlying']} → scenario {primary} | duration: {fc['duration_hint']}")
            for h, data in sorted(fc.get("cpcs_forecast", {}).get(primary, {}).items()):
                print(f"    CPCS T+{h}: CAR ~{data.get('expected_car_pct'):+.2f}%")

    if reality_checks:
        print("\n── B3: Reality Check / Slippage ──")
        for rc in reality_checks[:5]:
            print(f"  [{rc['aligned_date']}] {rc['underlying']} → {rc['verdict']}")
            for h, act in rc.get("cpcs_actual", {}).items():
                slip = rc.get("cpcs_slippage", {}).get(h, {})
                print(
                    f"    CPCS T+{h}: actual CAR {act.get('car_pct'):+.2f}% | "
                    f"slippage {slip.get('car_error_pct'):+.2f}%"
                )

    print("=" * 120 + "\n")


def build_summary_payload(
    symbol: Optional[str],
    horizon_stats: dict,
    cw_horizon_stats: dict,
    exposures: List[dict],
    forecasts: List[dict],
    reality_checks: List[dict],
    news_count: int = 0,
) -> Dict[str, Any]:
    """JSON-serializable summary for API responses."""
    return {
        "ticker": (symbol or "").upper() or None,
        "news_events_analyzed": news_count,
        "cpcs_car_summary": {
            str(h): {
                "count": st.get("count"),
                "mean_car_pct": round(st.get("mean_car", 0) * 100, 2),
                "p_up_car_pct": round(st.get("p_up_car", 0) * 100, 1),
                "p_value": st.get("p_value"),
            }
            for h, st in horizon_stats.items()
        },
        "cw_car_summary": {
            str(h): {
                "count": st.get("count"),
                "mean_car_pct": round(st.get("mean_car", 0) * 100, 2),
                "by_tier": st.get("by_tier", {}),
            }
            for h, st in cw_horizon_stats.items()
        },
        "exposure_assessments": exposures,
        "forecasts": forecasts,
        "reality_checks": reality_checks,
    }
