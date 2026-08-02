import datetime
from typing import Dict, Any, Optional, List
from src.core.database import SessionLocal, MarketOpportunity
from src.modules.cw_pricing.service import WarrantService
from src.api.routes.regime import get_ticker_regime
from src.modules.news_impact.service import NewsImpactService

def build_analyst_prompt(ticker: str, cw_symbol: Optional[str] = None) -> Dict[str, Any]:
    ticker = ticker.upper().strip()
    
    # 1. Fetch opportunities filtered by underlying
    opps_res = WarrantService.get_opportunities(strategy="balanced", underlying=ticker, limit=100)
    opps = opps_res.get("recommendations", [])
    
    # If a specific cw_symbol is requested, we prioritize/filter for it
    if cw_symbol:
        cw_symbol = cw_symbol.upper().strip()
        opps = [o for o in opps if o["warrant_symbol"] == cw_symbol]
        
    # 2. Fetch regime context
    regime_desc = "UNKNOWN"
    regime_confidence = "0.0%"
    mkt_regime_label = "UNKNOWN"
    try:
        regime_res = get_ticker_regime(ticker=ticker, days=252)
        if "regime_detector" in regime_res and "regime" in regime_res["regime_detector"]:
            regime_desc = regime_res["regime_detector"]["regime"]
        else:
            regime_desc = regime_res.get("regime_recommendation", "UNKNOWN")
        
        # Look at vnindex market regime
        from src.api.routes.regime import get_market_regime
        mkt_regime = get_market_regime()
        mkt_regime_label = mkt_regime.get("regime", "UNKNOWN")
        regime_confidence = f"{mkt_regime.get('confidence', 0.0) * 100:.1f}%"
    except Exception:
        pass
        
    # 3. Fetch sentiment / ML news signal
    sentiment_score = 0.0
    ml_outperform_prob = 50.0
    try:
        sentiment_res = NewsImpactService.get_news_impact(ticker)
        sentiment_score = sentiment_res.get("sentiment_score", 0.0)
        ml_res = NewsImpactService.get_ml_signal(ticker)
        ml_outperform_prob = ml_res.get("outperform_probability", 0.5) * 100.0
    except Exception:
        pass
        
    # 4. Process CW candidates & format Markdown table
    processed_opps = []
    avg_iv_hv = 1.0
    total_iv_hv = 0.0
    valid_count = 0
    
    cheapest_vol_symbol = "N/A"
    cheapest_iv_hv = 999.0
    expensive_vol_symbol = "N/A"
    expensive_iv_hv = 0.0
    
    for o in opps:
        price = o.get("market_price", 0.0)
        iv = o.get("implied_volatility_pct", 0.0)
        hv = o.get("historical_volatility_pct", 0.0)
        
        # Estimate spread_pct based on price
        if price < 500:
            spread = 5.0
        elif price < 1000:
            spread = 3.5
        elif price < 2000:
            spread = 2.5
        elif price < 5000:
            spread = 1.5
        else:
            spread = 1.0
            
        iv_hv_ratio = iv / hv if hv > 0 else 1.0
        
        if iv_hv_ratio < cheapest_iv_hv:
            cheapest_iv_hv = iv_hv_ratio
            cheapest_vol_symbol = o["warrant_symbol"]
            
        if iv_hv_ratio > expensive_iv_hv:
            expensive_iv_hv = iv_hv_ratio
            expensive_vol_symbol = o["warrant_symbol"]
            
        total_iv_hv += iv_hv_ratio
        valid_count += 1
        
        theta = abs(o.get("theta_daily_burn", 0.0))
        theta_pct_daily = (theta / price * 100.0) if price > 0 else 0.0
        
        processed_opps.append({
            "symbol": o["warrant_symbol"],
            "underlying": o["underlying_symbol"],
            "issuer": o["issuer"],
            "last_price": price,
            "pct_change": o.get("price_change_pct", 0.0),
            "iv": iv,
            "hv_20d": hv,
            "iv_hv_ratio": round(iv_hv_ratio, 2),
            "delta": o.get("delta", 0.0),
            "theta": theta,
            "theta_pct_daily": round(theta_pct_daily, 2),
            "spread_pct": spread,
            "maturity_days": o.get("days_to_maturity", 0),
            "score": o.get("composite_g_score", 0.0),
            "signal": o.get("recommendation_signal", "HOLD")
        })
        
    avg_iv_hv = total_iv_hv / valid_count if valid_count > 0 else 1.0
    
    # Render table in Markdown
    headers = ["symbol", "underlying", "issuer", "last_price", "pct_change", "iv", "hv_20d", "iv_hv_ratio", "delta", "theta", "theta_pct_daily", "spread_pct", "maturity_days", "score", "signal"]
    cw_data_table_markdown = "| " + " | ".join(headers) + " |\n"
    cw_data_table_markdown += "| " + " | ".join(["---"] * len(headers)) + " |\n"
    for p in processed_opps:
        row_vals = [str(p[h]) for h in headers]
        cw_data_table_markdown += "| " + " | ".join(row_vals) + " |\n"
        
    # Build full prompt
    analysis_date = datetime.datetime.now().strftime("%d/%m/%Y")
    
    prompt = f"""# PHÂN TÍCH COVERED WARRANT — FINVISTA AI ANALYST

## Bối cảnh thị trường
- Ngày phân tích: {analysis_date}
- VNINDEX Regime: {mkt_regime_label} (confidence: {regime_confidence})
- Underlying: {ticker}
- Bối cảnh user: Khách hàng cá nhân, tìm kiếm cơ hội tối ưu hóa danh mục Covered Warrants ngắn hạn.

## Dữ liệu CW (từ FINVISTA)
{cw_data_table_markdown}

## Chỉ số tổng hợp đã tính
- IV/HV trung bình basket: {avg_iv_hv:.2f}
- Mã rẻ vol nhất: {cheapest_vol_symbol} (IV/HV = {cheapest_iv_hv:.2f})
- Mã đắt vol nhất: {expensive_vol_symbol} (IV/HV = {expensive_iv_hv:.2f})

---

Thực hiện phân tích theo 4 bước:
0. IV/HV Pre-check (BẮT BUỘC)
1. Hard Filter (Delta ≥ 0.3, Maturity > 45d, Spread < 15%)
2. Two-Factor Analysis (Technical + Fundamental + GEX)
3. Kết luận: MUA/CHỜ/ĐỨNG NGOÀI + Entry/SL/TP + Theta decay %

Trả lời bằng tiếng Việt. Kết luận dứt khoát, không vague.
"""

    return {
        "prompt": prompt,
        "data_injected": {
            "analysis_date": analysis_date,
            "market_regime": mkt_regime_label,
            "regime_confidence": regime_confidence,
            "underlying_ticker": ticker,
            "avg_iv_hv": round(avg_iv_hv, 2),
            "cheapest_vol_symbol": cheapest_vol_symbol,
            "cheapest_iv_hv": round(cheapest_iv_hv, 2) if cheapest_iv_hv != 999.0 else 0.0,
            "expensive_vol_symbol": expensive_vol_symbol,
            "expensive_iv_hv": round(expensive_iv_hv, 2)
        },
        "cw_candidates": processed_opps
    }
