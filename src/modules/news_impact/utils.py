# -*- coding: utf-8 -*-
"""
Shared helpers for the News Impact dual-layer pipeline (CPCS + CW).
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from src.core.utils import logger

TIER1_ISSUERS = {"SSI", "HSC", "ACBS", "VCI", "VIETCAP"}
HV_CACHE_PATH = os.path.join("configs", "underlying_hv_cache.json")

OFFICIAL_KEYWORDS = [
    "công bố", "báo cáo tài chính", "đại hội", "đhcđ", "nghị quyết",
    "niêm yết", "phát hành", "công văn", "thông báo", "kết quả kinh doanh",
]
CORRIDOR_KEYWORDS = [
    "nguồn tin", " được biết", "rò rỉ", "đồn", "dự kiến", "có thể",
    "theo lời", "hành lang",
]
MACRO_KEYWORDS = [
    "lãi suất", "ngân hàng nhà nước", "vn-index", "vnindex", "vĩ mô",
    "bất động sản", "ngành", "thị trường", "fed", "cpi",
]


def classify_news_type(title: str, category: str = "") -> str:
    """Classify news as OFFICIAL, CORRIDOR, MACRO_SECTOR, or GENERAL."""
    text = f"{title} {category}".lower()
    if any(k in text for k in OFFICIAL_KEYWORDS):
        return "OFFICIAL"
    if any(k in text for k in CORRIDOR_KEYWORDS):
        return "CORRIDOR"
    if any(k in text for k in MACRO_KEYWORDS):
        return "MACRO_SECTOR"
    return "GENERAL"


def issuer_tier(issuer: str) -> str:
    code = (issuer or "").upper().strip()
    if code in TIER1_ISSUERS:
        return "TIER1"
    if code == "KIS":
        return "KIS"
    return "OTHER"


def load_hv_cache(underlying: str) -> Optional[float]:
    if not os.path.exists(HV_CACHE_PATH):
        return None
    try:
        with open(HV_CACHE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        entry = data.get(underlying.upper())
        if entry and "hv" in entry:
            return float(entry["hv"])
    except Exception as e:
        logger.debug(f"HV cache read failed for {underlying}: {e}")
    return None


def compute_pre_positioning(
    df_prices: pd.DataFrame,
    aligned_date,
    windows: Optional[List[int]] = None,
) -> Dict[str, Any]:
    """Measure spot run-up before an event (buy-the-rumor proxy)."""
    windows = windows or [5, 10, 20]
    result: Dict[str, Any] = {
        "returns": {},
        "buy_rumor_risk": False,
        "max_pre_run_pct": 0.0,
    }
    if df_prices is None or df_prices.empty:
        return result

    df = df_prices.copy()
    df["date"] = pd.to_datetime(df["date"]).dt.date
    match = df[df["date"] == aligned_date]
    if match.empty:
        return result

    idx = match.index[0]
    ref_close = float(df.iloc[idx]["close"])
    if ref_close <= 0:
        return result

    for w in windows:
        if idx >= w:
            base = float(df.iloc[idx - w]["close"])
            if base > 0:
                result["returns"][f"mom_{w}d"] = (ref_close - base) / base

    max_run = max(result["returns"].values()) if result["returns"] else 0.0
    result["max_pre_run_pct"] = max_run
    result["buy_rumor_risk"] = max_run >= 0.15
    return result


def load_cw_basket_for_underlying(underlying: str, db_session=None) -> List[Dict[str, Any]]:
    """Return live CW contracts for an underlying from market_opportunities."""
    from src.core.database import MarketOpportunity, SessionLocal

    underlying = underlying.upper().strip()
    close_db = False
    if db_session is None:
        db_session = SessionLocal()
        close_db = True

    basket: List[Dict[str, Any]] = []
    try:
        rows = (
            db_session.query(MarketOpportunity)
            .filter(MarketOpportunity.underlying == underlying)
            .order_by(MarketOpportunity.gearing.desc())
            .all()
        )
        for row in rows:
            iv = float(row.implied_volatility_pct or 0.0)
            hv = float(row.historical_volatility_pct or 0.0)
            basket.append(
                {
                    "cw_symbol": row.symbol,
                    "underlying": row.underlying,
                    "issuer": row.issuer,
                    "issuer_tier": issuer_tier(row.issuer),
                    "price": float(row.price or 0.0),
                    "strike": float(row.strike_price or 0.0),
                    "ratio": row.ratio or "1:1",
                    "gearing": float(row.gearing or 0.0),
                    "days_to_maturity": int(row.days_to_maturity or 0),
                    "iv_pct": iv,
                    "hv_pct": hv,
                    "iv_premium_pts": iv - hv,
                    "delta": float(row.delta or 0.0),
                    "vega": float(row.vega or 0.0),
                    "theta": float(row.theta_burn_day or 0.0),
                    "moneyness": row.moneyness_category or "UNKNOWN",
                    "underlying_price": float(row.underlying_price or 0.0),
                }
            )
    finally:
        if close_db:
            db_session.close()
    return basket


def summarize_cw_basket(basket: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not basket:
        return {
            "count": 0,
            "issuers": [],
            "avg_gearing": 0.0,
            "avg_iv_premium_pts": 0.0,
            "iv_crush_risk": "UNKNOWN",
        }
    premiums = [b["iv_premium_pts"] for b in basket if b.get("iv_pct")]
    avg_premium = float(np.mean(premiums)) if premiums else 0.0
    return {
        "count": len(basket),
        "issuers": sorted({b["issuer"] for b in basket if b.get("issuer")}),
        "tier1_count": sum(1 for b in basket if b.get("issuer_tier") == "TIER1"),
        "kis_count": sum(1 for b in basket if b.get("issuer_tier") == "KIS"),
        "avg_gearing": float(np.mean([b.get("gearing", 0.0) for b in basket])),
        "avg_iv_premium_pts": avg_premium,
        "iv_crush_risk": "HIGH" if avg_premium >= 5 else "MEDIUM" if avg_premium >= 2 else "LOW",
    }


def parse_event_date(event_date: str) -> Optional[datetime]:
    if not event_date:
        return None
    try:
        return pd.to_datetime(event_date).to_pydatetime()
    except Exception:
        return None


def safe_pct(value: Optional[float], digits: int = 2) -> Optional[float]:
    if value is None or (isinstance(value, float) and (np.isnan(value) or np.isinf(value))):
        return None
    return round(float(value) * 100, digits)
