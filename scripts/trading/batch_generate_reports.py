import asyncio
import os
import sys
import csv
from datetime import datetime
from typing import List, Dict

from jinja2 import Template

# Ensure project root is in path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.modules.trading_engine.ai_committee_service import AICommitteeService
from src.core.database import SessionLocal, MarketOpportunity

# ============================================================
# CẤU HÌNH
# ============================================================
MAX_CONCURRENT = 3  # Số mã phân tích song song tối đa
TEMPLATE_PATH = os.path.join(project_root, "src", "templates", "report_template.html")
OUTPUT_DIR = os.path.join(project_root, "data", "processed")


def get_all_symbols() -> List[str]:
    """Lấy danh sách các mã chứng quyền đang có cơ hội (Market Opportunities) từ Database."""
    db = SessionLocal()
    try:
        # Lấy top 15 mã có điểm cao nhất hoặc đang được quan tâm
        opportunities = db.query(MarketOpportunity).order_by(MarketOpportunity.score.desc()).limit(15).all()
        return [opp.symbol for opp in opportunities]
    except Exception as e:
        print(f"❌ Lỗi khi lấy danh sách mã từ DB: {e}")
        return []
    finally:
        db.close()


async def generate_report_for_symbol(
    symbol: str,
    service: AICommitteeService,
    template: Template,
    semaphore: asyncio.Semaphore,
) -> Dict:
    """Phân tích và xuất báo cáo HTML cho 1 mã. Trả về dict tóm tắt dùng cho báo cáo tổng hợp."""
    async with semaphore:
        print(f"🤖 [{symbol}] Đang thu thập dữ liệu Hội đồng AI...")
        try:
            result = await service.analyze_opportunity(symbol)
        except Exception as e:
            print(f"❌ [{symbol}] Lỗi khi phân tích: {e}")
            return {"symbol": symbol, "status": "error", "reason": str(e)}

        if result.get("status") != "completed":
            reason = result.get("reason", "Không rõ nguyên nhân")
            print(f"⚠️  [{symbol}] Phân tích không thành công: {reason}")
            return {"symbol": symbol, "status": "skipped", "reason": reason}

        reports = result.get("committee_reports", {})
        decision = result.get("decision", {})
        scenarios = result.get("scenarios", {})
        quant = reports.get("quant", {})
        credit = reports.get("credit", {})

        formatted_scenarios = [
            {"name": "Bull", "prob": scenarios.get("bull_case", {}).get("prob", 0), "color": "bg-emerald-500"},
            {"name": "Base", "prob": scenarios.get("base_case", {}).get("prob", 0), "color": "bg-amber-500"},
            {"name": "Bear", "prob": scenarios.get("bear_case", {}).get("prob", 0), "color": "bg-rose-500"},
        ]

        context = {
            "symbol": symbol,
            "date": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "decision": decision.get("decision", "SKIP"),
            "confidence_score": decision.get("confidence_score", 0),
            "target_upside": scenarios.get("bull_case", {}).get("target_pct", "N/A"),
            "z_score": round(credit.get("credit_metrics", {}).get("altman_z_score", 0), 2),
            "distress_prob": round(credit.get("credit_metrics", {}).get("bankruptcy_probability", 0) * 100, 2),
            "gearing": round(quant.get("gearing", 0), 2),
            "delta": round(quant.get("delta", 0), 3),
            "iv": round(quant.get("iv", 0), 1),
            "hv": round(quant.get("hv", 0), 1),
            "rationale_summary": decision.get("rationale_summary", ""),
            "debate_summary": reports.get("debate", "").replace("\n", "<br>"),
            "scenarios": formatted_scenarios,
        }

        html_out = template.render(context)
        output_filename = f"Finvista_Report_{symbol}.html"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_out)

        print(f"✅ [{symbol}] Đã tạo báo cáo: {output_path}")

        return {
            "symbol": symbol,
            "status": "completed",
            "decision": context["decision"],
            "confidence_score": context["confidence_score"],
            "z_score": context["z_score"],
            "distress_prob": context["distress_prob"],
            "file": output_filename,
        }


def build_summary_html(results: List[Dict], generated_at: str) -> str:
    """Tạo 1 báo cáo tổng hợp liệt kê toàn bộ mã đã chạy, kèm link tới báo cáo chi tiết từng mã."""
    completed = [r for r in results if r["status"] == "completed"]
    skipped = [r for r in results if r["status"] != "completed"]

    def decision_badge(d: str) -> str:
        color = {"STRONG BUY": "#059669", "BUY": "#10b981", "SELL": "#f43f5e", "HOLD": "#f59e0b"}.get(d, "#94a3b8")
        return f'<span style="background:{color};color:white;padding:4px 10px;border-radius:6px;font-size:12px;font-weight:bold;">{d}</span>'

    rows = "\n".join(
        f"""<tr style="border-bottom: 1px solid #f1f5f9; transition: background 0.2s;" onmouseover="this.style.background='#f8fafc'" onmouseout="this.style.background='transparent'">
            <td style="padding:12px; font-weight:700; color:#0f172a;">{r['symbol']}</td>
            <td style="padding:12px;">{decision_badge(r['decision'])}</td>
            <td style="padding:12px; font-weight:600;">{r['confidence_score']}/100</td>
            <td style="padding:12px;">{r['z_score']}</td>
            <td style="padding:12px; color:{'#10b981' if r['distress_prob'] < 30 else '#ef4444'}; font-weight:600;">{r['distress_prob']}%</td>
            <td style="padding:12px;"><a href="{r['file']}" style="color:#2563eb; text-decoration:none; font-weight:500;" target="_blank">📄 View Research</a></td>
        </tr>"""
        for r in sorted(completed, key=lambda x: (x.get("confidence_score") or 0), reverse=True)
    )

    skipped_items = "\n".join(
        f"<li style='margin-bottom:4px;'><strong>{r['symbol']}</strong>: <span style='color:#64748b;'>{r.get('reason', 'Không rõ')}</span></li>" for r in skipped
    )

    return f"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<title>Finvista Master Dashboard - AI Committee Reports</title>
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    body {{ font-family: 'Inter', sans-serif; background-color: #f8fafc; color: #1e293b; margin: 0; padding: 40px; }}
    .container {{ max-width: 1100px; margin: auto; background: white; padding: 40px; border-radius: 16px; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1); }}
    h1 {{ font-size: 32px; font-weight: 800; color: #0f172a; margin-bottom: 8px; letter-spacing: -0.025em; }}
    .meta {{ color: #64748b; font-size: 14px; margin-bottom: 32px; border-bottom: 1px solid #e2e8f0; pb: 16px; }}
    table {{ width: 100%; border-collapse: collapse; text-align: left; }}
    th {{ padding: 12px; background: #f1f5f9; color: #475569; font-size: 12px; text-transform: uppercase; letter-spacing: 0.05em; font-weight: 700; }}
    .skipped-box {{ margin-top: 40px; padding: 24px; background: #fff1f2; border-radius: 12px; border-left: 4px solid #f43f5e; }}
    .skipped-box h3 {{ color: #9f1239; margin-top: 0; }}
</style>
</head>
<body>
  <div class="container">
    <div style="display:flex; justify-content:space-between; align-items:flex-end; margin-bottom:24px;">
        <div>
            <h1>📊 Finvista Master Dashboard</h1>
            <p class="meta">AI COMMITTEE CONSOLIDATED INTELLIGENCE REPORT</p>
        </div>
        <div style="text-align:right; font-size:12px; color:#94a3b8;">
            Generated: {generated_at}
        </div>
    </div>
    
    <div style="display:grid; grid-template-cols: repeat(3, 1fr); gap:20px; margin-bottom:32px;">
        <div style="background:#f0f9ff; padding:20px; border-radius:12px; border:1px solid #bae6fd;">
            <div style="font-size:12px; color:#0369a1; font-weight:700; text-transform:uppercase;">Total Scanned</div>
            <div style="font-size:24px; font-weight:800; color:#0c4a6e;">{len(results)}</div>
        </div>
        <div style="background:#f0fdf4; padding:20px; border-radius:12px; border:1px solid #bbf7d0;">
            <div style="font-size:12px; color:#15803d; font-weight:700; text-transform:uppercase;">Completed</div>
            <div style="font-size:24px; font-weight:800; color:#064e3b;">{len(completed)}</div>
        </div>
        <div style="background:#fff1f2; padding:20px; border-radius:12px; border:1px solid #fecdd3;">
            <div style="font-size:12px; color:#be123c; font-weight:700; text-transform:uppercase;">Failed/Skipped</div>
            <div style="font-size:24px; font-weight:800; color:#881337;">{len(skipped)}</div>
        </div>
    </div>

    <table>
      <thead>
        <tr>
          <th>Symbol</th>
          <th>Decision</th>
          <th>Confidence</th>
          <th>Z-Score</th>
          <th>Distress Prob</th>
          <th>Action</th>
        </tr>
      </thead>
      <tbody>
        {rows}
      </tbody>
    </table>

    {f'''
    <div class="skipped-box">
      <h3>⚠️ Exceptions & Skip Logs</h3>
      <ul style="font-size:13px; color:#475569;">{skipped_items}</ul>
    </div>
    ''' if skipped else ""}
    
    <div style="margin-top:40px; text-align:center; color:#94a3b8; font-size:11px;">
        &copy; 2026 Finvista Quant Pro. All Research is AI-Augmented.
    </div>
  </div>
</body>
</html>"""


async def generate_all_reports():
    print("🔎 Đang lấy danh sách các mã tiềm năng từ Database...")
    symbols = get_all_symbols()
    
    if not symbols:
        print("❌ Không tìm thấy mã nào để phân tích. Hãy đảm bảo bạn đã chạy 'python run.py cw' trước.")
        return
        
    print(f"📋 Tìm thấy {len(symbols)} mã tiềm năng: {', '.join(symbols)}\n")

    service = AICommitteeService()

    if not os.path.exists(TEMPLATE_PATH):
        print(f"❌ Không tìm thấy template tại: {TEMPLATE_PATH}")
        return

    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        template = Template(f.read())

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    tasks = [generate_report_for_symbol(s, service, template, semaphore) for s in symbols]
    results = await asyncio.gather(*tasks)

    generated_at = datetime.now().strftime("%d/%m/%Y %H:%M")
    summary_html = build_summary_html(results, generated_at)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    summary_filename = f"Finvista_Master_Dashboard_{timestamp}.html"
    summary_path = os.path.join(OUTPUT_DIR, summary_filename)
    
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(summary_html)

    completed_count = sum(1 for r in results if r["status"] == "completed")
    print(f"\n🎉 HOÀN TẤT BÁO CÁO TỔNG HỢP")
    print(f"--------------------------------------------------")
    print(f"✅ Hoàn thành: {completed_count}/{len(symbols)} mã.")
    print(f"📑 Dashboard: {summary_path}")
    print(f"💡 Mở dashboard để truy cập tất cả báo cáo chi tiết.")


if __name__ == "__main__":
    asyncio.run(generate_all_reports())
