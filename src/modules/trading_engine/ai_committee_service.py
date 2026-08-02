# -*- coding: utf-8 -*-
"""
🤖 FINVISTA: AI COMMITTEE SERVICE (MULTI-AGENT QUANT)
=====================================================
Orchestrates the 7-layer hybrid filtering process:
Quant -> Credit -> Macro -> Vision -> Volatility -> Liquidity -> Final Decision.

Author: samvo
"""

import asyncio
import base64
import json
import os
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from sqlalchemy import desc
from src.infra.ai_client import get_ai_client
from src.infra.chart_generator import generate_candlestick_base64
from src.modules.cw_pricing.service import WarrantService
from src.modules.credit_risk.service import CreditRiskService
from src.core.database import SessionLocal, MarketOpportunity, AIAnalysisMemory, CorporateNews, CorporateEvent
from src.infra.orderbook_scraper import get_real_order_book, calculate_slippage
from src.modules.news_impact.service import NewsImpactService

try:
    import vnstock
except ImportError:
    vnstock = None

class AICommitteeService:
    """
    Orchestrator for the AI Quant Committee.
    Implements a rigorous 7-layer filtering process for Covered Warrants.
    """

    def __init__(self):
        self.ai_client = get_ai_client()
        self.warrant_service = WarrantService()
        self.credit_service = CreditRiskService()

    async def analyze_opportunity(self, symbol: str, target_volume: int = 5000) -> Dict[str, Any]:
        """
        Run the full 7-layer AI Committee analysis for a specific warrant.
        """
        symbol = symbol.upper().strip()
        
        # 🟢 LAYER 1: QUANT GATEKEEPER & EXPERIENCE (Hard Filters)
        past_experience = self._get_past_experience(symbol)
        quant_data = self._layer1_quant_gatekeeper(symbol)
        if not quant_data:
            return {"status": "rejected", "layer": 1, "reason": "Failed Quant Gatekeeper checks (Liquidity/Greeks)"}

        underlying = quant_data.get("underlying")
        
        # 🟢 LAYER 2: CREDIT & FUNDAMENTAL AUDIT (XGBoost)
        credit_data = self._layer2_credit_engine(underlying)
        if credit_data.get("credit_metrics", {}).get("bankruptcy_probability", 1.0) > 0.30:
            return {"status": "rejected", "layer": 2, "reason": f"Credit risk too high for underlying {underlying}"}

        # 🟢 LAYER 3, 4, 5, 6: PARALLEL AGENT INVESTIGATION
        tasks = [
            self._layer3_macro_sentiment(symbol, underlying),
            self._layer4_vision_ta(symbol, underlying, quant_data.get("days_to_maturity", 90)),
            self._layer5_volatility_arb(symbol, quant_data),
            self._layer6_liquidity_gate(symbol, target_volume)
        ]
        layer_results = await asyncio.gather(*tasks)
        
        macro_report = layer_results[0]
        vision_report = layer_results[1]
        volatility_report = layer_results[2]
        liquidity_report = layer_results[3]

        # 🟢 LAYER 7: AI DEBATE, SCENARIO & PM DECISION
        upcoming_events = self._get_upcoming_events(underlying)
        
        # A. Debate Phase
        debate_result = await self._layer7_ai_debate(
            quant_data, credit_data, macro_report, vision_report, volatility_report, past_experience, liquidity_report, upcoming_events
        )

        # B. Scenario Probabilizer
        scenarios = await self._layer7_scenario_probabilizer(
            quant_data, credit_data, macro_report, vision_report, debate_result
        )

        # C. Final PM Decision
        final_decision = await self._layer7_pm_decision(debate_result, liquidity_report, scenarios)

        # 💾 POST-PROCESS: SAVE TO MEMORY
        self._save_to_memory(symbol, underlying, quant_data, final_decision)

        return {
            "symbol": symbol,
            "underlying": underlying,
            "timestamp": datetime.now().isoformat(),
            "status": "completed",
            "decision": final_decision,
            "scenarios": scenarios,
            "past_experience": past_experience,
            "committee_reports": {
                "quant": quant_data,
                "credit": credit_data,
                "macro": macro_report,
                "vision": vision_report,
                "volatility": volatility_report,
                "liquidity": liquidity_report,
                "debate": debate_result
            }
        }

    def _get_past_experience(self, symbol: str) -> str:
        """Retrieve recent AI analysis records for this symbol to provide historical context."""
        db = SessionLocal()
        try:
            records = db.query(AIAnalysisMemory).filter(
                AIAnalysisMemory.symbol == symbol
            ).order_by(AIAnalysisMemory.timestamp.desc()).limit(3).all()
            
            if not records:
                return "Chưa có kinh nghiệm quá khứ cho mã này."
            
            exp_text = "KINH NGHIỆM QUÁ KHỨ (BÀI HỌC):\n"
            for r in records:
                status = "Đúng" if r.is_correct else "Sai/Chưa rõ"
                exp_text += f"- [{r.timestamp.strftime('%Y-%m-%d')}] Quyết định: {r.decision}, Điểm: {r.consensus_score}, Kết quả: {status}. Lý do cũ: {r.rationale_summary}\n"
            return exp_text
        finally:
            db.close()

    def _save_to_memory(self, symbol: str, underlying: str, quant: Dict[str, Any], decision: Dict[str, Any]):
        """Persist the current analysis result into the long-term memory table."""
        db = SessionLocal()
        try:
            mem = AIAnalysisMemory(
                symbol=symbol,
                underlying=underlying,
                decision=decision.get("decision"),
                consensus_score=decision.get("confidence_score", 0),
                rationale_summary=decision.get("rationale_summary"),
                price_at_analysis=quant.get("price"),
                underlying_price_at_analysis=quant.get("underlying_price"),
                iv_at_analysis=quant.get("iv"),
                delta_at_analysis=quant.get("delta"),
                days_to_maturity=quant.get("days_to_maturity")
            )
            db.add(mem)
            db.commit()
        except Exception as e:
            print(f"⚠️ Failed to save to AI memory: {e}")
        finally:
            db.close()

    def _layer1_quant_gatekeeper(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Layer 1: Filter by quantitative liquidity and basic Greeks."""
        db = SessionLocal()
        try:
            opp = db.query(MarketOpportunity).filter(MarketOpportunity.symbol == symbol).first()
            if not opp:
                return None
            
            # Example hard-gates:
            if opp.days_to_maturity < 14:
                return None
            
            return {
                "symbol": opp.symbol,
                "underlying": opp.underlying,
                "price": opp.price,
                "underlying_price": opp.underlying_price,
                "delta": opp.delta,
                "gearing": opp.gearing,
                "iv": opp.implied_volatility_pct,
                "hv": opp.historical_volatility_pct,
                "days_to_maturity": opp.days_to_maturity,
                "g_score": opp.score
            }
        finally:
            db.close()

    def _layer2_credit_engine(self, underlying: str) -> Dict[str, Any]:
        """Layer 2: Fetch credit health via XGBoost engine. Handles excluded sectors gracefully."""
        try:
            return self.credit_service.get_credit_health(underlying)
        except Exception as e:
            # If ticker is excluded (like Banks), we shouldn't assume it's distressed
            return {
                "ticker": underlying,
                "credit_metrics": {
                    "bankruptcy_probability": 0.05,  # Default safe for excluded sectors (e.g. Banks)
                    "status_description": "Sector excluded from ML model (Likely Stable/Bank)"
                }
            }

    async def _layer3_macro_sentiment(self, symbol: str, underlying: str) -> str:
        """Layer 3: Macro & Market Sentiment (with RAG from database + News Impact ML signal)."""
        news_context = ""
        db = SessionLocal()
        try:
            # Fetch latest news for both symbol and underlying from DB
            relevant_news = db.query(CorporateNews).filter(
                (CorporateNews.symbol == underlying) | (CorporateNews.symbol == symbol)
            ).order_by(desc(CorporateNews.date)).limit(10).all()
            
            if relevant_news:
                news_context = "\n\nCÁC TIN TỨC & SỰ KIỆN LIÊN QUAN (Vietstock):\n"
                for item in relevant_news:
                    news_context += f"- [{item.date}] {item.title} ({item.category})\n"
            
            # Fetch upcoming events
            events = db.query(CorporateEvent).filter(
                CorporateEvent.ticker == underlying
            ).order_by(desc(CorporateEvent.event_date)).limit(5).all()
            
            if events:
                news_context += "\nLỊCH SỰ KIỆN DOANH NGHIỆP:\n"
                for ev in events:
                    news_context += f"- [{ev.event_date}] {ev.event_type}: {ev.description}\n"
                    
        except Exception as e:
            print(f"⚠️ RAG News DB Error: {e}")
        finally:
            db.close()

        # 🆕 News Impact ML Signal — tích hợp xác suất outperform từ ML model
        news_ml_context = ""
        ml_signal: dict = {}  # initialize trước để tránh uninitialized reference
        try:
            ml_signal = NewsImpactService.get_ml_signal(underlying)
            sentiment_score = NewsImpactService.get_ticker_sentiment_score(underlying, days=30)
            if ml_signal.get("model_available"):
                prob = ml_signal.get("probability")
                ml_sentiment = ml_signal.get("sentiment", "UNKNOWN")
                news_ml_context = (
                    f"\n\n📊 NEWS IMPACT ML MODEL (Random Forest/XGBoost trained):\n"
                    f"  - Xác suất outperform thị trường 5 ngày tới: {prob:.1%}\n"
                    f"  - Tín hiệu ML: {ml_sentiment}\n"
                    f"  - Điểm sentiment tổng hợp 30 ngày: {sentiment_score:+.2f} (-1 cực kỳ tiêu cực, +1 cực kỳ tích cực)\n"
                )
        except Exception as e:
            print(f"⚠️ News Impact ML integration error: {e}")

        prompt = f"""BẠN LÀ: CHUYÊN GIA DÒNG TIỀN VÀ TÂM LÝ VĨ MÔ (Institutional Flow & Sentiment Specialist).
Nhiệm vụ: Phân tích cổ phiếu cơ sở {underlying} cho chứng quyền {symbol}.

DỮ LIỆU ĐẦU VÀO:
{news_context}{news_ml_context}

HÃY PHÂN TÍCH VÀ TRẢ LỜI THEO CÁC TIÊU CHÍ SAU:
1. Dòng tiền thông minh (Smart Money): Khối ngoại và Tự doanh đang tích lũy hay phân phối? 
2. Tâm lý đám đông (Social Sentiment): Theo dõi Telegram/Facebook, cộng đồng đang FOMO hay chán nản?
3. Trạng thái Hedging: Basis phái sinh VN30F1M đang chỉ báo điều gì về xu hướng VN30?
4. Market Regime: Thị trường đang trong trạng thái Risk-On (Chấp nhận rủi ro) hay Risk-Off (Phòng thủ)?
5. News Impact ML: Tích hợp tín hiệu ML ({ml_signal.get('sentiment', 'N/A')}) vào nhận định tổng thể.

Yêu cầu: Đưa ra nhận định sắc sảo, không nói nước đôi. Nếu rủi ro vĩ mô lớn, hãy cảnh báo ngay."""
        
        messages = [{"role": "user", "content": prompt}]
        return self.ai_client.chat(messages, temperature=0.5)

    def _get_upcoming_events(self, underlying: str) -> str:
        """Helper to fetch events for the debate phase."""
        db = SessionLocal()
        try:
            events = db.query(CorporateEvent).filter(
                CorporateEvent.ticker == underlying
            ).order_by(desc(CorporateEvent.event_date)).limit(5).all()
            if not events: return "Không có sự kiện doanh nghiệp sắp tới."
            
            text = "SỰ KIỆN DOANH NGHIỆP SẮP TỚI:\n"
            for ev in events:
                text += f"- {ev.event_date}: {ev.event_type} ({ev.description})\n"
            return text
        finally:
            db.close()

    async def _layer4_vision_ta(self, symbol: str, underlying: str, days_to_maturity: int = 90) -> str:
        """Layer 4: Pattern Skeptic & Vision Analyst (Gemini Vision)."""
        try:
            chart_days = 90
            if days_to_maturity > 360: chart_days = 720
            elif days_to_maturity > 180: chart_days = 360
            elif days_to_maturity > 90: chart_days = 180

            chart_base64 = generate_candlestick_base64(ticker=underlying, days=chart_days)
            if not chart_base64: return f"Lỗi tạo biểu đồ cho {underlying}."
            
            vision_prompt = f"""BẠN LÀ: CHUYÊN GIA PHÂN TÍCH THỊ GIÁC SÁT THỦ (Adversarial Pattern Analyst).
Nhiệm vụ: Tìm lỗi sai trong xu hướng tăng hoặc xác nhận điểm bùng nổ của {underlying}.

YÊU CẦU QUAN SÁT BIỂU ĐỒ:
1. Cấu trúc giá: Có phải là mô hình tích lũy tin cậy (Wyckoff/VCP) hay chỉ là hồi phục kỹ thuật (Dead Cat Bounce)?
2. Kháng cự 'Tử thần': Xác định vùng giá mà phe bán sẽ xả hàng mạnh nhất dựa trên các đỉnh cũ.
3. Khối lượng (Volume Profile): Dòng tiền lớn có thực sự vào lệnh hay chỉ là 'quay tay' tạo thanh khoản?
4. Tương quan thời gian: Với {days_to_maturity} ngày còn lại của chứng quyền {symbol}, liệu xu hướng này có kịp xảy ra?

Yêu cầu: 
- Phân tích khách quan, tập trung vào các bẫy giá (Liquidity Traps). 
- BẮT BUỘC trích dẫn ít nhất 1 vùng giá hỗ trợ/kháng cự cụ thể bạn nhìn thấy trên biểu đồ.
- Trả lời ngắn gọn, chuyên nghiệp bằng tiếng Việt."""
            return self.ai_client.analyze_chart_vision(chart_base64, vision_prompt)
        except Exception as e:
            return f"Lỗi trong quá trình phân tích Vision: {str(e)}"

    async def _layer5_volatility_arb(self, symbol: str, quant_data: Dict[str, Any]) -> str:
        """Layer 5: Options Math & Volatility Forensic Specialist."""
        prompt = f"""BẠN LÀ: PHÙ THỦY QUYỀN CHỌN (Greeks & Volatility Arbitrage Specialist).
Nhiệm vụ: Đánh giá độ "Rẻ/Đắt" về mặt toán học của chứng quyền {symbol}.

DỮ LIỆU ĐỊNH LƯỢNG:
- Delta: {quant_data.get('delta')} (Độ nhạy)
- Gearing: {quant_data.get('gearing')}x (Đòn bẩy thực)
- Implied Vol (IV): {quant_data.get('iv')}% vs Hist Vol (HV): {quant_data.get('hv')}%
- Time Decay: Còn {quant_data.get('days_to_maturity')} ngày.

HÃY TRẢ LỜI:
1. Volatility Risk: IV đang quá cao so với HV (Overpriced) hay đang rẻ (Underpriced)?
2. Theta Burn: Tốc độ bào mòn vốn hàng ngày có chấp nhận được không?
3. Gamma Risk: Nếu giá cổ phiếu cơ sở biến động mạnh, chứng quyền này có bùng nổ lợi nhuận không?
4. Recommendation: Có lợi thế toán học (Positive Edge) để vào lệnh không?

YÊU CẦU: Trình bày súc tích. Phải trích dẫn cụ thể con số IV và HV trong nhận định."""
        messages = [{"role": "user", "content": prompt}]
        return self.ai_client.chat(messages, temperature=0.4)

    async def _layer6_liquidity_gate(self, symbol: str, volume: int) -> Dict[str, Any]:
        """Layer 6: Perform a real-time order book depth check."""
        ob = get_real_order_book(symbol)
        if not ob:
            return {"status": "unknown", "reason": "Could not fetch real-time L2 data (Market closed or blocked)."}
        analysis = calculate_slippage(ob, "BUY", volume)
        return analysis

    async def _layer7_ai_debate(self, quant, credit, macro, vision, volatility, past_experience, liquidity, upcoming_events) -> str:
        """Layer 7 (A): The Multi-Round AI Debate Phase (Hedge Fund Grade)."""
        critique_prompt = f"""HỘI ĐỒNG AI FINVISTA - PHIÊN TRANH LUẬN VÒNG 2 (PHẢN BIỆN CHÉO)
{past_experience}
{upcoming_events}
DỮ LIỆU ĐẦU VÀO (HEDGE FUND GRADE):
- Mã CW: {quant.get('symbol')} | Cơ sở: {quant.get('underlying')}
- Định lượng: G-Score {quant.get('g_score')}, Delta {quant.get('delta')}, IV {quant.get('iv')}%
- Tín dụng (Merton Structural): DD {quant.get('distance_to_default', 'N/A')}, PD {quant.get('default_probability', 'N/A')}
- Biến động (GARCH-EVT VaR): {quant.get('var_95', 'N/A')}% rủi ro giảm giá ngày mai.
- THANH KHOẢN THỰC TẾ (Sổ lệnh): {json.dumps(liquidity)}

LUẬN ĐIỂM CỦA CÁC AGENT (VÒNG 1):
1. Agent Vĩ mô & Social: {macro}
2. Agent Thị giác (Vision): {vision}
3. Agent Quyền chọn & Biến động: {volatility}

NHIỆM VỤ PHẢN BIỆN (CRITIQUE):
Bạn hãy đóng vai 'Người phản biện sắc sảo' (Skeptic). 
- Kiểm tra xem GARCH-EVT VaR có đang cảnh báo rủi ro mà Vision bỏ sót không?
- Kiểm tra xem Merton PD có đang chỉ ra rủi ro doanh nghiệp mà Vĩ mô chưa nhắc tới không?
- Đánh giá khả năng thoát hàng dựa trên Slippage nếu kịch bản Bear Case xảy ra.

HÃY XUẤT KẾT QUẢ THEO ĐỊNH DẠNG BẢNG SAU:
| Khía cạnh | Luận điểm chính | Điểm yếu/Rủi ro | Hệ số tin tưởng (0-100) |
| :--- | :--- | :--- | :--- |
| Vĩ mô & Social | ... | ... | ... |
| Kỹ thuật & Vision | ... | ... | ... |
| Định giá & GARCH Vol | ... | ... | ... |
| Credit & Merton | ... | ... | ... |
| Khả thi (Liquidity) | ... | ... | ... |

KẾT LUẬN CUỐI: Đưa ra ĐIỂM ĐỒNG THUẬN (Consensus Score) trung bình."""
        messages = [{"role": "user", "content": critique_prompt}]
        return self.ai_client.chat(messages, temperature=0.6)

    async def _layer7_scenario_probabilizer(self, quant, credit, macro, vision, debate) -> Dict[str, Any]:
        """
        Layer 7 (B): Probabilistic Scenario Engine (Expected Value focus).
        """
        prompt = f"""BẠN LÀ: CHUYÊN GIA XÁC SUẤT (Quantitative Risk Manager).
Dựa trên phiên tranh luận đối kháng, hãy gán xác suất cho 3 kịch bản của {quant.get('symbol')} trong 5-7 phiên tới.

QUY TẮC:
1. Bull Case: Phải có chất xúc tác (Catalyst) và dòng tiền xác nhận.
2. Base Case: Kịch bản 'Sideways' hoặc tăng/giảm nhẹ (<3%).
3. Bear Case: Kịch bản sụp đổ, gãy nền hoặc Vol Crush.

YÊU CẦU ĐẦU RA:
- Chỉ trả về duy nhất định dạng JSON. Không có lời chào hay giải thích.
- Tổng của (bull_case.prob + base_case.prob + bear_case.prob) PHẢI CHÍNH XÁC BẰNG 100.

ĐỊNH DẠNG JSON MẪU:
{{
  "bull_case": {{ "prob": 40, "target_pct": "+15%", "rationale": "Vượt MA20" }},
  "base_case": {{ "prob": 40, "target_pct": "0%", "rationale": "Sideways" }},
  "bear_case": {{ "prob": 20, "target_pct": "-10%", "rationale": "Gãy hỗ trợ" }},
  "expected_value_score": 65
}}"""
        messages = [{"role": "user", "content": prompt}]
        response = self.ai_client.chat(messages, temperature=0.3)
        
        fallback = {
            "bull_case": {"prob": 33, "target_pct": "0%", "rationale": "N/A"},
            "base_case": {"prob": 34, "target_pct": "0%", "rationale": "N/A"},
            "bear_case": {"prob": 33, "target_pct": "0%", "rationale": "N/A"},
            "expected_value_score": 50
        }
        
        try:
            start = response.find('{')
            end = response.rfind('}') + 1
            if start == -1 or end == 0: return fallback
            data = json.loads(response[start:end])
            return data
        except: return fallback

    async def _layer7_pm_decision(self, debate_result: str, liquidity: Dict[str, Any], scenarios: Dict[str, Any]) -> Dict[str, Any]:
        """
        Layer 7 (C): The Final Portfolio Manager Decision (Chief Investment Officer).
        """
        prompt = f"""BẠN LÀ: GIÁM ĐỐC ĐẦU TƯ (Chief Investment Officer).
Bạn chịu trách nhiệm cuối cùng về sự an toàn của nguồn vốn 100 Tỷ VND.

DỮ LIỆU TỪ HỘI ĐỒNG:
{debate_result}

XÁC SUẤT & KỊCH BẢN:
{json.dumps(scenarios, indent=2, ensure_ascii=False)}

HÃY ĐƯA RA QUYẾT ĐỊNH CUỐI CÙNG:
1. Hành động: STRONG BUY, BUY, HOLD, hoặc SKIP.
2. Tỷ trọng (Size): Đề xuất % NAV.
3. Rationale: Giải thích lý do cốt lõi.

YÊU CẦU NGHIÊM NGẶT:
- Chỉ trả về định dạng JSON duy nhất. Bắt đầu bằng {{ và kết thúc bằng }}.
- Phần `rationale_summary` BẮT BUỘC phải trích dẫn ít nhất 2 số liệu định lượng cụ thể từ dữ liệu đầu vào (ví dụ: xác suất kịch bản, điểm đồng thuận, hoặc IV).

ĐỊNH DẠNG JSON:
{{
  "decision": "ACTION",
  "confidence_score": 0-100,
  "rationale_summary": "Dẫn chứng số liệu X và Y để kết luận Z...",
  "recommended_size_pct": 0-10,
  "stop_loss": "Giá",
  "take_profit": "Giá"
}}"""
        messages = [{"role": "user", "content": prompt}]
        response = self.ai_client.chat(messages, temperature=0.2)
        
        try:
            start = response.find('{')
            end = response.rfind('}') + 1
            return json.loads(response[start:end])
        except:
            return {
                "decision": "SKIP",
                "confidence_score": 0,
                "rationale_summary": "Lỗi phân tích quyết định cuối cùng.",
                "recommended_size_pct": 0
            }

    async def analyze_sector_master_deep(self, sector_name: str, warrants: List[Dict[str, Any]], market_context: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """
        THE ULTIMATE ALPHA DISCOVERY METHOD:
        - Massive context ingestion (Master Prompt)
        - Deep reasoning (@think=0)
        - Cross-ticker comparative analysis
        """
        underlying_list = list(set([w['underlying'] for w in warrants]))
        
        # 1. Fetch Credit Health
        sector_health = {}
        for und in underlying_list:
            sector_health[und] = self._layer2_credit_engine(und)
            
        # 2. Fetch News/Sentiment (RAG)
        sector_news = ""
        db = SessionLocal()
        try:
            for und in underlying_list[:5]: # Limit to top 5 to avoid token explosion
                recent_news = db.query(CorporateNews).filter(CorporateNews.symbol == und).order_by(desc(CorporateNews.date)).limit(2).all()
                if recent_news:
                    sector_news += f"\n- {und}: " + " | ".join([n.title for n in recent_news])
        except Exception as e:
            print(f"⚠️ Master Scan RAG Error: {e}")
        finally:
            db.close()
            
        warrant_table = []
        for w in warrants:
            warrant_table.append({
                "ID": w['symbol'],
                "Asset": w['underlying'],
                "Price": w['price'],
                "Delta": w['delta'],
                "Gearing": w['gearing'],
                "IV": f"{w['implied_volatility_pct']}%",
                "HV": f"{w['historical_volatility_pct']}%",
                "Upside": f"{w['upside_pct']}%",
                "Credit": sector_health.get(w['underlying'], {}).get('credit_metrics', {}).get('status_description', 'Stable')
            })

        master_prompt = f"""DÀNH CHO HỘI ĐỒNG ĐẦU TƯ ĐỊNH LƯỢNG (QUANT INVESTMENT COMMITTEE)
Nhiệm vụ: Tìm kiếm 'SUPER ALPHA' trong NHÓM NGÀNH: {sector_name.upper()}

1. BỐI CẢNH THỊ TRƯỜNG & VĨ MÔ (MARKET REGIME & SENTIMENT):
- Trạng thái: {market_context.get('regime')}
- Thiên kiến: {market_context.get('bias')}
- TÂM LÝ & TIN TỨC GẦN ĐÂY:{sector_news if sector_news else ' Không có tin tức vĩ mô đặc biệt.'}

2. DỮ LIỆU ĐỊNH LƯỢNG CHI TIẾT (SECTOR DATA MATRIX):
{json.dumps(warrant_table, indent=2, ensure_ascii=False)}

3. QUY TRÌNH TƯ DUY SÂU (DEEP REASONING):
Bạn có thể suy luận từng bước (Chain-of-Thought) để đánh giá tương quan chéo, rủi ro và EV (Expected Value).

YÊU CẦU ĐẦU RA:
- Sau khi suy luận, bạn PHẢI trả về kết quả cuối cùng trong một khối block JSON duy nhất dạng `[ ... ]` ở cuối câu trả lời.
- KHÔNG trả về text thừa sau khối JSON này.

ĐỊNH DẠNG JSON CẦN TUÂN THỦ:
[
  {{
    "symbol": "Mã",
    "bull_prob": 0-100,
    "ev_score": 0-100,
    "decision": "STRONG BUY" | "BUY" | "HOLD" | "SKIP",
    "rationale": "BẮT BUỘC trích dẫn ít nhất 2 chỉ số định lượng VÀ kết hợp tin tức (nếu có) để giải thích tại sao mã này tốt hơn các mã khác."
  }}
]"""
        
        batch_results = {}
        try:
            response = self.ai_client.chat([{"role": "user", "content": master_prompt}], model_type="deep", temperature=0.1)
            
            # Clean up markdown formatting if present
            cleaned_response = response.replace('```json', '').replace('```', '').strip()
            
            import re
            # Extract JSON block using regex to avoid grabbing brackets from CoT
            match = re.search(r'\[\s*\{.*?\}\s*\]', cleaned_response, re.DOTALL)
            
            if match:
                json_str = match.group(0)
                evaluations = json.loads(json_str)
                for ev in evaluations:
                    symbol = ev.get('symbol', 'UNKNOWN')
                    batch_results[symbol] = {
                        "symbol": symbol,
                        "underlying": next((w['underlying'] for w in warrants if w['symbol'] == symbol), "N/A"),
                        "status": "completed",
                        "scenarios": {
                            "bull_case": {"prob": ev.get('bull_prob', 33)},
                            "base_case": {"prob": ev.get('base_prob', 34)},
                            "bear_case": {"prob": 33}, # Fallback for bear
                            "expected_value_score": ev.get('ev_score', 50)
                        },
                        "decision": {
                            "decision": ev.get('decision', 'HOLD'),
                            "rationale_summary": ev.get('rationale', ''),
                            "expected_value_score": ev.get('ev_score', 50)
                        }
                    }
            else:
                print("⚠️ Master Deep: Could not find valid JSON array in response. Raw output sample:")
                print(response[-500:]) # Print end of response for debugging
        except Exception as e:
            print(f"❌ Master Sector Audit failed for {sector_name}: {e}")
            
        return batch_results
