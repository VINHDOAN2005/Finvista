# -*- coding: utf-8 -*-
"""
🤖 FINVISTA: AI CHAT ENDPOINT
==============================
AI-powered financial chat assistant using Gemini integration.

Author: samvo
"""

import re
from typing import List, Dict, Optional
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel

router = APIRouter(prefix="/api/chat", tags=["AI Chat"])


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    model: Optional[str] = None
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None


class ChatResponse(BaseModel):
    response: str
    model: str
    usage: Optional[Dict] = None


async def get_optional_current_user(request: Request) -> Optional[dict]:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ")[1]
    try:
        from src.api.dependencies import get_current_user
        return get_current_user(token)
    except Exception:
        return None



@router.post("/", response_model=ChatResponse)
async def chat_completion(request: ChatRequest, req_raw: Request):
    """
    AI-powered financial chat assistant with personalized context integration.
    """
    try:
        from src.infra.ai_client import get_ai_client
        
        ai_client = get_ai_client()
        
        # Check if AI client is properly configured
        if ai_client.use_web_api and not ai_client._is_port_open(8081):
            raise HTTPException(
                status_code=503,
                detail="AI service unavailable. Please configure OPENROUTER_API_KEY in environment variables."
            )
        
        # 1. Resolve optional logged-in user
        current_user = await get_optional_current_user(req_raw)
        
        # 2. Extract mentioned symbols from conversation history
        last_message = request.messages[-1].content if request.messages else ""
        candidate_symbols = []
        for msg in request.messages:
            candidate_symbols.extend(re.findall(r'\b[A-Z]{3,4}\b', msg.content))
        
        # Verify which ones are actual stock symbols in database
        symbols = []
        if candidate_symbols:
            try:
                from src.core.database import SessionLocal, StockHistoricalPrice, CompanyFinancial
                db_sess = SessionLocal()
                try:
                    valid_stock_symbols = {s[0].upper() for s in db_sess.query(StockHistoricalPrice.symbol).distinct().all()}
                    valid_company_tickers = {c[0].upper() for c in db_sess.query(CompanyFinancial.ticker).distinct().all()}
                    all_valid_symbols = valid_stock_symbols.union(valid_company_tickers)
                    for sym in set(candidate_symbols):
                        if sym.upper() in all_valid_symbols:
                            symbols.append(sym.upper())
                finally:
                    db_sess.close()
            except Exception:
                # Fallback to simple filtering if db query fails
                EXCLUDE_KEYWORDS = {"ICR", "OCF", "ROA", "ROE", "HMM", "QUY", "MUA", "SAI", "EBIT", "SHAP", "NAV"}
                for sym in set(candidate_symbols):
                    if sym.upper() not in EXCLUDE_KEYWORDS:
                        symbols.append(sym.upper())
        
        # 3. Gather quantitative contexts
        system_context = []
        
        # 3.1 Market Regime
        try:
            from src.modules.regime_analysis.indicators.hmm_regime import calculate_vnindex_regime
            regime = calculate_vnindex_regime(days=1250)
            system_context.append(
                f"TRẠNG THÁI THỊ TRƯỜNG HIỆN TẠI (HMM Model):\n"
                f"- Regime: {regime.get('regime', 'UNKNOWN')}\n"
                f"- Bias: {regime.get('bias', 'NEUTRAL')}\n"
                f"- Confidence: {regime.get('confidence', 0.0) * 100:.1f}%\n"
                f"- Mô tả: {regime.get('description', '')}\n"
            )
        except Exception:
            pass
            
        # 3.2 User's Portfolio
        if current_user:
            try:
                from src.modules.trading_engine.portfolio_service import PortfolioService
                port = PortfolioService.get_portfolio(username=current_user["username"])
                if port and port.get("status") == "success":
                    assets = port.get("assets", [])
                    asset_str = ""
                    for a in assets:
                        asset_str += f"  + {a['symbol']}: Số lượng {a['qty']}, Giá vốn {a['avg_price']:,} VNĐ, Giá hiện tại {a['market_price']:,} VNĐ, Lãi/Lỗ: {a['pnl_pct']:.2f}%\n"
                    system_context.append(
                        f"DANH MỤC ĐẦU TƯ CỦA NGƯỜI DÙNG ({current_user['username']}):\n"
                        f"- Số dư tiền mặt: {port.get('cash', 0):,} VNĐ\n"
                        f"- Tổng giá trị tài sản: {port.get('total_value', 0):,} VNĐ\n"
                        f"- Tài sản đang nắm giữ:\n{asset_str if asset_str else '  (Chưa nắm giữ tài sản nào)'}\n"
                    )
            except Exception:
                pass
                
        # 3.3 Ticker Specific Data (News & Events)
        ticker_info = ""
        for sym in set(symbols):
            try:
                from src.modules.cw_pricing.service import WarrantService
                news_res = WarrantService.get_news(symbol=sym, limit=3)
                news_list = news_res.get("news", [])
                if news_list:
                    ticker_info += f"Tin tức gần đây của {sym}:\n"
                    for n in news_list:
                        ticker_info += f"  - [{n['date']}] {n['title']}: {n['summary'] or ''}\n"
            except Exception:
                pass
                
            try:
                from src.modules.cw_pricing.service import WarrantService
                event_res = WarrantService.get_events(ticker=sym, limit=2)
                events = event_res.get("events", [])
                if events:
                    ticker_info += f"Sự kiện sắp tới của {sym}:\n"
                    for ev in events:
                        ticker_info += f"  - [{ev['event_date']}] {ev['event_type']}: {ev['description']}\n"
            except Exception:
                pass

            # Query financials & credit risk from SQLite
            try:
                from src.core.database import SessionLocal, CompanyFinancial, CompanyDistressAnalysis
                db_sess = SessionLocal()
                try:
                    fins = db_sess.query(CompanyFinancial).filter(CompanyFinancial.ticker == sym).order_by(CompanyFinancial.year.desc()).all()
                    distress = db_sess.query(CompanyDistressAnalysis).filter(CompanyDistressAnalysis.ticker == sym).order_by(CompanyDistressAnalysis.year.desc()).all()
                    
                    if fins:
                        ticker_info += f"Dữ liệu BCTC thực tế của {sym} trong hệ thống:\n"
                        for f in fins:
                            ticker_info += (
                                f"  - Năm {f.year}: Doanh thu {f.net_revenue:,.0f} VND, LNST {f.profit_after_tax:,.0f} VND, "
                                f"Tổng tài sản {f.total_assets:,.0f} VND, Tổng nợ {f.total_liabilities:,.0f} VND, "
                                f"Vốn chủ sở hữu {f.total_equity:,.0f} VND, Dòng tiền HĐKD {f.operating_cash_flow:,.0f} VND\n"
                            )
                    if distress:
                        ticker_info += f"Chỉ số tài chính & Phân tích rủi ro của {sym} trong hệ thống:\n"
                        for d in distress:
                            ticker_info += (
                                f"  - Năm {d.year}: Tỷ số thanh toán hiện hành {d.current_ratio:.2f}, "
                                f"Tỷ lệ nợ/tài sản {d.debt_ratio:.2f}, ROAA {d.roaa*100:.2f}%, ROAE {d.roae*100:.2f}%, "
                                f"Altman Z-Score {d.altman_z_score:.2f}, Merton Probability of Default {d.merton_pd*100:.2f}%\n"
                            )
                finally:
                    db_sess.close()
            except Exception:
                pass
                
        if ticker_info:
            system_context.append(f"THÔNG TIN DOANH NGHIỆP TRUY VẤN:\n{ticker_info}")
            
        # 3.4 Ranked Opportunities
        try:
            from src.modules.cw_pricing.service import WarrantService
            opps = WarrantService.get_opportunities(limit=5)
            opps_list = opps.get("recommendations", [])
            if opps_list:
                opps_str = ""
                for o in opps_list:
                    opps_str += f"  - {o['warrant_symbol']} (Cơ sở: {o['underlying_symbol']}): Tín hiệu {o['recommendation_signal']}, G-Score {o['composite_g_score']}, Greeks Delta {o['delta']}, Giá {o['market_price']} VNĐ\n"
                system_context.append(f"TOP CƠ HỘI ĐẦU TƯ CHỨNG QUYỀN (G-Score cao nhất):\n{opps_str}")
        except Exception:
            pass

        # 3.5 Query BCTC/Annual Report via RAG if the user asks about financial reports
        try:
            years_mentioned = [int(y) for y in re.findall(r'\b(20\d{2})\b', last_message)]
            report_keywords = ["bctc", "báo cáo tài chính", "báo cáo thường niên", "báo cáo", "annual report", "năm", "vòng quay", "số liệu", "data"]
            is_asking_about_reports = any(kw in last_message.lower() for kw in report_keywords)
            
            if is_asking_about_reports and symbols:
                if not years_mentioned:
                    for msg in reversed(request.messages[:-1]):
                        years = [int(y) for y in re.findall(r'\b(20\d{2})\b', msg.content)]
                        if years:
                            years_mentioned = years
                            break
                
                query_year = years_mentioned[0] if years_mentioned else 2025
                report_rag_context = ""
                for sym in set(symbols):
                    from src.modules.annual_reports.manager import AnnualReportManager
                    report_mgr = AnnualReportManager()
                    rag_answer = report_mgr.query_report(
                        ticker=sym,
                        year=query_year,
                        quarter=5,
                        question=last_message
                    )
                    if rag_answer and not rag_answer.startswith("❌"):
                        report_rag_context += f"  - Kết quả RAG từ BCTC {sym} năm {query_year}: {rag_answer}\n"
                
                if report_rag_context:
                    system_context.append(f"KẾT QUẢ TRUY VẤN RAG BCTC DÀNH CHO CÂU HỎI HIỆN TẠI:\n{report_rag_context}")
        except Exception:
            pass
            
        # 4. Construct personalized system message
        import datetime
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        system_prompt = (
            "Bạn là Finvista AI, trợ lý ảo tư vấn tài chính chuyên nghiệp cấp cao (CFA).\n"
            f"Thời gian hiện tại của hệ thống: {current_time}.\n"
            "Dưới đây là thông tin thực tế từ hệ thống dữ liệu định lượng của ứng dụng Finvista. "
            "Hãy sử dụng những thông tin này để trả lời câu hỏi của người dùng một cách cá nhân hóa, "
            "chính xác và thực tế nhất.\n\n"
            "QUY TẮC VẼ BIỂU ĐỒ:\n"
            "Khi người dùng yêu cầu vẽ biểu đồ hoặc đồ thị cho một mã chứng quyền cụ thể (ví dụ: CACB2511) hoặc một cổ phiếu cơ sở cụ thể (ví dụ: FPT, MBB, ACB), bạn bắt buộc phải viết "
            "token đặc biệt [CHART: Mã] (ví dụ: [CHART: CACB2511] hoặc [CHART: FPT]) ở một dòng riêng biệt trong phản hồi của bạn. Hệ thống sẽ tự động bắt lấy token này "
            "để hiển thị biểu đồ kỹ thuật tương tác trực quan thực tế (chứa lịch sử giá) cực kỳ đẹp mắt ngay tại vị trí đó.\n\n"
        )
        system_prompt += "\n".join(system_context)
        
        # Convert Pydantic models to dicts and prepend system message
        messages_dict = [{"role": "system", "content": system_prompt}] + [
            {"role": msg.role, "content": msg.content}
            for msg in request.messages
        ]
        
        response = ai_client.chat(
            messages=messages_dict,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )
        
        if not response:
            raise HTTPException(
                status_code=500,
                detail="AI service returned empty response"
            )
        
        return ChatResponse(
            response=response,
            model=request.model or ai_client.default_model
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Chat completion failed: {str(e)}"
        )


@router.post("/financial-commentary")
async def generate_financial_commentary(
    ticker: str,
    current_ratio: float,
    debt_ratio: float,
    altman_z_score: float,
    profit_after_tax: float = 0.0,
    operating_cash_flow: float = 0.0,
    ebit_to_interest: float = 9999.0
):
    """
    Generate AI-powered financial commentary for distressed companies.
    
    This endpoint provides the same functionality used in Telegram alerts
    but accessible via REST API.
    """
    try:
        from src.infra.ai_client import get_ai_client
        
        ai_client = get_ai_client()
        
        commentary = ai_client.generate_financial_commentary(
            ticker=ticker,
            current_ratio=current_ratio,
            debt_ratio=debt_ratio,
            altman_z_score=altman_z_score,
            profit_after_tax=profit_after_tax,
            operating_cash_flow=operating_cash_flow,
            ebit_to_interest=ebit_to_interest
        )
        
        if not commentary:
            raise HTTPException(
                status_code=500,
                detail="AI service returned empty commentary"
            )
        
        return {
            "ticker": ticker,
            "commentary": commentary,
            "model": ai_client.default_model
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Financial commentary generation failed: {str(e)}"
        )


@router.post("/trading-signal-commentary")
async def generate_trading_signal_commentary(
    cw_code: str,
    signal: str,
    g_score: float,
    price: float,
    leverage: float,
    days_to_expiry: int,
    price_change_pct: float
):
    """
    Generate AI-powered commentary for CW trading signals.
    
    This endpoint provides AI analysis for trading signals
    used in the quantitative trading system.
    """
    try:
        from src.infra.ai_client import get_ai_client
        
        ai_client = get_ai_client()
        
        commentary = ai_client.generate_trading_signal_commentary(
            cw_code=cw_code,
            signal=signal,
            g_score=g_score,
            price=price,
            leverage=leverage,
            days_to_expiry=days_to_expiry,
            price_change_pct=price_change_pct
        )
        
        if not commentary:
            raise HTTPException(
                status_code=500,
                detail="AI service returned empty commentary"
            )
        
        return {
            "cw_code": cw_code,
            "signal": signal,
            "commentary": commentary,
            "model": ai_client.default_model
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Trading signal commentary generation failed: {str(e)}"
        )
