# -*- coding: utf-8 -*-
"""
📊 FINVISTA: MULTI-SOURCE ORDER BOOK (L2) SCRAPER
=================================================
Fetches real-time market depth from various brokerage gateways.
Provides fallback mechanisms to ensure high availability.

Author: samvo
"""

import requests
import json
from typing import Dict, Any, List, Optional

def get_order_book_ssi(symbol: str) -> Optional[Dict[str, Any]]:
    """Try fetching from SSI GraphQL gateway."""
    url = "https://iboard.ssi.com.vn/gateway/graphql"
    query = """
    query stockDetails($symbols: [String]) {
      stockDetails(symbols: $symbols) {
        symbol
        bestBid1 priceBid1 volBid1
        bestBid2 priceBid2 volBid2
        bestBid3 priceBid3 volBid3
        bestOffer1 priceOffer1 volOffer1
        bestOffer2 priceOffer2 volOffer2
        bestOffer3 priceOffer3 volOffer3
      }
    }
    """
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Content-Type": "application/json",
        "Referer": "https://iboard.ssi.com.vn/"
    }
    try:
        r = requests.post(url, json={"query": query, "variables": {"symbols": [symbol]}}, headers=headers, timeout=5)
        if r.status_code == 200:
            data = r.json().get("data", {}).get("stockDetails", [])
            if data:
                d = data[0]
                res = {"symbol": symbol, "bids": [], "asks": []}
                for i in range(1, 4):
                    if d.get(f"priceBid{i}"):
                        res["bids"].append({"price": float(d[f"priceBid{i}"]), "volume": int(d[f"volBid{i}"])})
                    if d.get(f"priceOffer{i}"):
                        res["asks"].append({"price": float(d[f"priceOffer{i}"]), "volume": int(d[f"volOffer{i}"])})
                return res
    except: pass
    return None

def get_order_book_vps(symbol: str) -> Optional[Dict[str, Any]]:
    """Try fetching from VPS API."""
    url = f"https://bgapidatafeed.vps.com.vn/getstocksnapshot/{symbol}"
    try:
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            d = r.json()
            res = {"symbol": symbol, "bids": [], "asks": []}
            for i in range(1, 4):
                p_bid = d.get(f"bidPrice{i}")
                v_bid = d.get(f"bidVol{i}")
                if p_bid: res["bids"].append({"price": float(p_bid), "volume": int(v_bid)})
                p_ask = d.get(f"offerPrice{i}")
                v_ask = d.get(f"offerVol{i}")
                if p_ask: res["asks"].append({"price": float(p_ask), "volume": int(v_ask)})
            return res
    except: pass
    return None

def get_real_order_book(symbol: str) -> Optional[Dict[str, Any]]:
    """Master function that tries all sources."""
    res = get_order_book_ssi(symbol)
    if res and (res["bids"] or res["asks"]): return res
    res = get_order_book_vps(symbol)
    if res and (res["bids"] or res["asks"]): return res
    return None

def calculate_slippage(order_book: Dict[str, Any], side: str, target_vol: int) -> Dict[str, Any]:
    """Calculate effective price and slippage for a target volume."""
    if not order_book:
        return {"error": "No liquidity data available at the moment."}
        
    levels = order_book["asks"] if side == "BUY" else order_book["bids"]
    if not levels:
        return {"error": "Order book is empty. Symbol might be inactive or market closed."}
        
    total_filled = 0
    total_cost = 0.0
    
    for lv in levels:
        to_fill = min(target_vol - total_filled, lv["volume"])
        total_filled += to_fill
        total_cost += to_fill * lv["price"]
        if total_filled >= target_vol: break
            
    if total_filled == 0:
        return {"error": "No orders available on this side."}
        
    avg_price = total_cost / total_filled
    best_price = levels[0]["price"]
    slippage_pct = abs((avg_price - best_price) / best_price) * 100
    
    return {
        "target_vol": target_vol,
        "filled_vol": total_filled,
        "avg_price": avg_price,
        "best_price": best_price,
        "slippage_pct": round(slippage_pct, 3),
        "is_fully_filled": total_filled >= target_vol
    }

def analyze_imbalance(symbol: str) -> Dict[str, Any]:
    ob = get_real_order_book(symbol)
    if not ob:
        return {"ratio": 0.5, "status": "NEUTRAL (No L2 Data)", "is_safe_to_buy": True}
        
    total_bid_vol = sum(level["volume"] for level in ob.get("bids", []))
    total_ask_vol = sum(level["volume"] for level in ob.get("asks", []))
    
    if total_bid_vol + total_ask_vol == 0:
        return {"ratio": 0.5, "status": "NEUTRAL (Empty Book)", "is_safe_to_buy": True}
        
    ratio = total_bid_vol / (total_bid_vol + total_ask_vol)
    
    if ratio < 0.35:
        status = "BEARISH (Heavy Selling Pressure)"
        is_safe = False
    elif ratio > 0.65:
        status = "BULLISH (Hidden Bids / Strong Support)"
        is_safe = True
    else:
        status = "NEUTRAL"
        is_safe = True
        
    return {"ratio": round(ratio, 3), "status": status, "is_safe_to_buy": is_safe}
