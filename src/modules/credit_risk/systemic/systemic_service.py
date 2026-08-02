# -*- coding: utf-8 -*-
"""
FINVISTA: SYSTEMIC RISK SERVICE
=================================
Service layer wrapping network_builder.py to expose:
  - get_top_propagators(n)       → top-N risk-propagating nodes
  - get_ticker_contagion(ticker) → systemic exposure for a specific ticker
  - get_network_summary()        → graph-level stats (nodes, edges, density)

Caches the expensive build_market_network() call for CACHE_TTL seconds.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from src.core.utils import logger

_CACHE_TTL_SECONDS = 1800  # 30 min — network rebuild is expensive
_cache: Dict[str, Any] = {}


def _get_network():
    """Lazy-build and cache the NetworkX market contagion graph."""
    now = datetime.now()
    if "graph" in _cache:
        age = (now - _cache["built_at"]).total_seconds()
        if age < _CACHE_TTL_SECONDS:
            return _cache["graph"]

    logger.info("🕸️ [SystemicService] Building market contagion network (cache miss)...")
    try:
        from src.modules.credit_risk.systemic.network_builder import build_market_network
        G = build_market_network()
        _cache["graph"] = G
        _cache["built_at"] = now
        logger.info(f"✅ [SystemicService] Network built: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges.")
        return G
    except Exception as e:
        logger.error(f"❌ [SystemicService] Network build failed: {e}")
        return None


class SystemicRiskService:
    """
    Service for systemic / contagion risk queries.
    All methods are stateless and safe to call concurrently.
    """

    @staticmethod
    def get_network_summary() -> Dict[str, Any]:
        """High-level graph statistics: nodes, edges, density, top propagators."""
        G = _get_network()
        if G is None:
            return {"status": "unavailable", "reason": "Network could not be built."}

        # Out-degree weighted sum → influence score
        out_weights = {}
        in_weights = {}
        for u, v, data in G.edges(data=True):
            w = data.get("weight", 0.0)
            out_weights[u] = out_weights.get(u, 0.0) + w
            in_weights[v] = in_weights.get(v, 0.0) + w

        top_propagators = sorted(out_weights.items(), key=lambda x: x[1], reverse=True)[:10]
        top_vulnerable = sorted(in_weights.items(), key=lambda x: x[1], reverse=True)[:10]

        propagator_details = []
        for ticker, score in top_propagators:
            nd = G.nodes.get(ticker, {})
            propagator_details.append({
                "ticker": ticker,
                "name": nd.get("name", ""),
                "industry": nd.get("industry", ""),
                "conglomerate": nd.get("conglomerate", "None"),
                "out_weight_score": round(score, 4),
                "base_risk": round(nd.get("base_risk", 0.0), 4),
                "risk_source": nd.get("risk_source", ""),
            })

        vulnerable_details = []
        for ticker, score in top_vulnerable:
            nd = G.nodes.get(ticker, {})
            vulnerable_details.append({
                "ticker": ticker,
                "name": nd.get("name", ""),
                "industry": nd.get("industry", ""),
                "in_weight_score": round(score, 4),
                "base_risk": round(nd.get("base_risk", 0.0), 4),
            })

        n = G.number_of_nodes()
        e = G.number_of_edges()
        density = round(e / (n * (n - 1)) if n > 1 else 0.0, 6)

        return {
            "status": "ok",
            "nodes": n,
            "edges": e,
            "density": density,
            "top_propagators": propagator_details,
            "top_vulnerable": vulnerable_details,
        }

    @staticmethod
    def get_ticker_contagion(ticker: str) -> Dict[str, Any]:
        """
        Systemic exposure profile for a single ticker:
          - Its own base_risk
          - Outbound influence (who it can spread risk to)
          - Inbound exposure (who can spread risk to it)
          - Conglomerate group
        """
        G = _get_network()
        ticker = ticker.upper().strip()

        if G is None:
            return {"status": "unavailable", "ticker": ticker}

        if ticker not in G.nodes:
            return {
                "status": "not_found",
                "ticker": ticker,
                "note": f"{ticker} không tìm thấy trong network. Có thể chưa có dữ liệu.",
            }

        nd = G.nodes[ticker]

        # Outbound: tickers that this node spreads risk TO
        out_edges = [
            {
                "target": v,
                "target_name": G.nodes[v].get("name", ""),
                "weight": round(d.get("weight", 0.0), 4),
            }
            for _, v, d in sorted(
                G.out_edges(ticker, data=True),
                key=lambda x: x[2].get("weight", 0.0),
                reverse=True,
            )[:10]
        ]

        # Inbound: tickers that spread risk TO this node
        in_edges = [
            {
                "source": u,
                "source_name": G.nodes[u].get("name", ""),
                "weight": round(d.get("weight", 0.0), 4),
            }
            for u, _, d in sorted(
                G.in_edges(ticker, data=True),
                key=lambda x: x[2].get("weight", 0.0),
                reverse=True,
            )[:10]
        ]

        total_out = sum(e["weight"] for e in out_edges)
        total_in = sum(e["weight"] for e in in_edges)

        # Systemic importance = (out + in) combined
        systemic_score = round(total_out + total_in, 4)
        if systemic_score > 0.5:
            importance_label = "SYSTEMICALLY_IMPORTANT"
        elif systemic_score > 0.2:
            importance_label = "MODERATE_LINKAGE"
        else:
            importance_label = "LOW_LINKAGE"

        return {
            "status": "ok",
            "ticker": ticker,
            "company_name": nd.get("name", ""),
            "industry": nd.get("industry", ""),
            "conglomerate": nd.get("conglomerate", "None"),
            "base_risk": round(nd.get("base_risk", 0.0), 4),
            "risk_source": nd.get("risk_source", ""),
            "market_cap_vnd": nd.get("market_cap", 0),
            "systemic_score": systemic_score,
            "importance_label": importance_label,
            "total_outbound_influence": round(total_out, 4),
            "total_inbound_exposure": round(total_in, 4),
            "top_outbound_targets": out_edges,
            "top_inbound_sources": in_edges,
        }

    @staticmethod
    def get_top_propagators(n: int = 10) -> List[Dict[str, Any]]:
        """Return top-N tickers ranked by outbound contagion influence."""
        summary = SystemicRiskService.get_network_summary()
        if summary.get("status") != "ok":
            return []
        return summary.get("top_propagators", [])[:n]
