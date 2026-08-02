import asyncio
import os
import sys
from datetime import datetime
from typing import List, Dict
from jinja2 import Template

# Ensure project root is in path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.core.database import SessionLocal, MarketOpportunity, CorporateNews
from src.infra.ai_client import get_ai_client

# ============================================================
# CẤU HÌNH
# ============================================================
OUTPUT_DIR = os.path.join(project_root, "data", "processed")

def get_market_data() -> List[Dict]:
    db = SessionLocal()
    try:
        opps = db.query(MarketOpportunity).order_by(MarketOpportunity.score.desc()).limit(15).all()
        data = []
        for o in opps:
            # Lấy tin tức mới nhất cho cổ phiếu cơ sở
            news = db.query(CorporateNews).filter(CorporateNews.symbol == o.underlying).order_by(CorporateNews.date.desc()).limit(2).all()
            news_titles = " | ".join([n.title for n in news]) if news else "Không có tin mới"
            
            data.append({
                "symbol": o.symbol,
                "underlying": o.underlying,
                "price": o.price,
                "score": round(o.score, 1),
                "gearing": round(o.gearing, 1),
                "iv": round(o.implied_volatility_pct, 1),
                "delta": round(o.delta, 2),
                "premium": round(o.premium_pct, 1),
                "news": news_titles
            })
        return data
    finally:
        db.close()

async def get_ai_master_summary(market_data: List[Dict]) -> str:
    ai_client = get_ai_client()
    
    prompt = f"""BẠN LÀ: GIÁM ĐỐC CHIẾN LƯỢC ĐẦU TƯ (Chief Investment Strategist).
Nhiệm vụ: Đánh giá tổng quan thị trường chứng quyền dựa trên danh sách Top 15 cơ hội dưới đây.

DANH SÁCH DỮ LIỆU:
{market_data}

YÊU CẦU:
1. Nhận định xu hướng chung của nhóm VN30 (cổ phiếu cơ sở).
2. Chỉ ra 3 mã chứng quyền "Sáng giá nhất" (Top Alpha) dựa trên sự kết hợp giữa Điểm số (Score), Đòn bẩy (Gearing) và Tin tức.
3. Cảnh báo rủi ro về IV (Volatility) hoặc Thanh khoản nếu có.
4. Đưa ra chiến lược hành động tổng quát cho danh mục (Ví dụ: Tăng tỷ trọng nhóm Bank, Thu hẹp nhóm BĐS...).

YÊU CẦU TRÌNH BÀY:
- Trình bày ngắn gọn, súc tích bằng tiếng Việt.
- Sử dụng các đầu dòng rõ ràng.
- BẮT BUỘC có phần "KẾT LUẬN CHIẾN LƯỢC" ở cuối."""

    messages = [{"role": "user", "content": prompt}]
    return ai_client.chat(messages, temperature=0.3)

def build_overview_html(summary: str, market_data: List[Dict], generated_at: str) -> str:
    rows = "\n".join(
        f"""<tr class="hover:bg-slate-50 transition-colors border-b border-slate-100">
            <td class="p-4 font-bold text-slate-900">{d['symbol']}</td>
            <td class="p-4 text-slate-600 font-semibold">{d['underlying']}</td>
            <td class="p-4 text-emerald-600 font-bold">{d['score']}</td>
            <td class="p-4 text-slate-700">{d['gearing']}x</td>
            <td class="p-4 text-slate-700">{d['iv']}%</td>
            <td class="p-4 text-slate-700">{d['delta']}</td>
            <td class="p-4 text-[11px] text-slate-500 italic max-w-xs truncate">{d['news']}</td>
        </tr>"""
        for d in market_data
    )

    return f"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <title>Finvista Fast Overview - Market Intelligence</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap'); body {{ font-family: 'Inter', sans-serif; }}</style>
</head>
<body class="bg-slate-50 p-10">
    <div class="max-w-5xl mx-auto bg-white rounded-2xl shadow-xl overflow-hidden border border-slate-200">
        <!-- Header -->
        <div class="bg-slate-900 p-8 text-white flex justify-between items-end">
            <div>
                <h1 class="text-3xl font-extrabold tracking-tight">FINVISTA <span class="text-amber-400">MARKET OVERVIEW</span></h1>
                <p class="text-slate-400 text-sm uppercase tracking-widest font-bold mt-1">Automated Intelligence Dashboard</p>
            </div>
            <div class="text-right text-slate-500 text-xs font-medium">Generated: {generated_at}</div>
        </div>

        <div class="p-8 space-y-10">
            <!-- AI Strategic Analysis -->
            <section>
                <div class="flex items-center gap-3 mb-4">
                    <div class="w-1.5 h-6 bg-amber-400 rounded-full"></div>
                    <h2 class="text-xl font-extrabold text-slate-800 uppercase tracking-tight">AI Strategic Summary</h2>
                </div>
                <div class="bg-slate-50 rounded-xl p-6 text-slate-700 leading-relaxed border border-slate-100 shadow-inner prose prose-slate max-w-none">
                    {summary.replace('\n', '<br>')}
                </div>
            </section>

            <!-- Top Opportunities Table -->
            <section>
                <div class="flex items-center gap-3 mb-4">
                    <div class="w-1.5 h-6 bg-blue-500 rounded-full"></div>
                    <h2 class="text-xl font-extrabold text-slate-800 uppercase tracking-tight">Top 15 Opportunities</h2>
                </div>
                <div class="overflow-hidden rounded-xl border border-slate-100 shadow-sm">
                    <table class="w-full text-left border-collapse">
                        <thead>
                            <tr class="bg-slate-50 text-[10px] uppercase tracking-wider font-bold text-slate-400">
                                <th class="p-4">Symbol</th>
                                <th class="p-4">Asset</th>
                                <th class="p-4">Score</th>
                                <th class="p-4">Gearing</th>
                                <th class="p-4">IV</th>
                                <th class="p-4">Delta</th>
                                <th class="p-4">Market News</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows}
                        </tbody>
                    </table>
                </div>
            </section>
        </div>

        <!-- Footer -->
        <div class="p-6 bg-slate-50 border-t border-slate-100 text-center text-[10px] text-slate-400 font-bold uppercase tracking-widest">
            &copy; 2026 Finvista Quant Pro - For Institutional Use Only
        </div>
    </div>
</body>
</html>"""

async def run_overview():
    print("🔎 Đang thu thập dữ liệu thị trường nhanh...")
    market_data = get_market_data()
    
    if not market_data:
        print("❌ Không có dữ liệu. Hãy chạy 'python run.py cw' trước.")
        return

    print("🤖 Đang chạy AI Master Summary cho toàn bộ danh mục...")
    summary = await get_ai_master_summary(market_data)
    
    generated_at = datetime.now().strftime("%d/%m/%Y %H:%M")
    html_content = build_overview_html(summary, market_data, generated_at)
    
    output_path = os.path.join(OUTPUT_DIR, f"Finvista_Market_Fast_Overview_{datetime.now().strftime('%H%M')}.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print(f"\n✅ HOÀN TẤT BÁO CÁO TỔNG QUAN NHANH")
    print(f"📑 Địa chỉ: {output_path}")
    print(f"💡 File này nhẹ và nhanh hơn 10 lần so với báo cáo chi tiết từng mã.")

if __name__ == "__main__":
    asyncio.run(run_overview())
