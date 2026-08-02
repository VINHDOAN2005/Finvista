# -*- coding: utf-8 -*-
"""
🚀 FINVISTA: TELEGRAM ALERTS ENGINE & WEBHOOK DISPATCHER
======================================================
Automated alert notifications for quantitative Covered Warrant anomalies:
- Imminent maturity risk warnings (< 14 days to expiry)
- Elite Investment Signal updates (STRONG BUY recommendations)

Author: samvo
"""

import os
import json
import requests
import html
from datetime import datetime

CONFIG_PATH = os.path.join("configs", "telegram_config.json")

def load_telegram_config() -> dict:
    """Load Telegram token, chat ID, and active status from configuration registry or environment variables."""
    from dotenv import load_dotenv
    load_dotenv()

    # Priority 1: Check environment variables
    env_token = os.getenv("TELEGRAM_BOT_TOKEN")
    env_chat_id = os.getenv("TELEGRAM_CHAT_ID")
    env_enabled_str = os.getenv("TELEGRAM_ALERTS_ENABLED", "").lower()
    
    # Check if they are configured in environment (not placeholders)
    if env_token and "YOUR_TELEGRAM" not in env_token and env_chat_id and "YOUR_TELEGRAM" not in env_chat_id:
        return {
            "telegram_bot_token": env_token,
            "telegram_chat_id": env_chat_id,
            "enable_alerts": env_enabled_str in ["true", "1", "yes"]
        }

    # Priority 2: Fallback to JSON config
    os.makedirs("configs", exist_ok=True)
    if not os.path.exists(CONFIG_PATH):
        # Create a default template with setup guidelines
        default_config = {
            "telegram_bot_token": "YOUR_TELEGRAM_BOT_TOKEN_HERE",
            "telegram_chat_id": "YOUR_TELEGRAM_CHAT_ID_HERE",
            "enable_alerts": False
        }
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(default_config, f, indent=4, ensure_ascii=False)
        return default_config
    
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ Failed to read Telegram configuration: {e}")
        return {}

def send_telegram_alert_batch(warrants_buy_signals: list, warrants_near_expiry: list):
    """
    Send a beautifully formatted, consolidated HTML alert message containing:
    - Elite quantitative picks (STRONG BUY warrants)
    - Qualified buy opportunities (BUY warrants)
    - Crucial Greek warnings (Days to Expiry < 14 days, highlighting Theta decay)
    - Interactive inline keyboard for quick actions
    """
    config = load_telegram_config()
    token = config.get("telegram_bot_token", "").strip()
    chat_id = config.get("telegram_chat_id", "").strip()
    enabled = config.get("enable_alerts", False)
    
    if not enabled:
        return
        
    if not token or "YOUR_TELEGRAM" in token or not chat_id or "YOUR_TELEGRAM" in chat_id:
        print("\n📢 [Telegram Alerts] Active alerts are ENABLED in config but credentials are not configured.")
        print(f"💡 Please edit the configuration file: {os.path.abspath(CONFIG_PATH)} to set your Bot Token & Chat ID.")
        return
        
    if not warrants_buy_signals and not warrants_near_expiry:
        print("💡 [Telegram Alerts] No alerts triggered (0 Buy signals and 0 Warrants < 14 days to expiry). Chat is kept clean.")
        return
        
    # Split signals
    strong_buys = [cw for cw in warrants_buy_signals if cw.get('U_Signal') == 'STRONG BUY']
    buys = [cw for cw in warrants_buy_signals if cw.get('U_Signal') == 'BUY']
        
    # Construct premium HTML message layout
    msg = "🚀 <b>[FINVISTA QUANT ALERTS]</b>\n"
    msg += f"📅 <i>{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</i>\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # Summary stats
    total_signals = len(strong_buys) + len(buys)
    msg += f"📊 <b>Tổng quan:</b> {total_signals} tín hiệu\n\n"
    
    if strong_buys:
        msg += f"💎 <b>STRONG BUY</b> ({len(strong_buys)} mã)\n"
        for cw in strong_buys:  # Show all STRONG BUY
            symbol = html.escape(str(cw['A_MaCW']))
            msg += (
                f"• <b>{symbol}</b> | Điểm: <b>{cw['G_Score']:.1f}</b> | "
                f"Giá: <b>{cw['C_GiaCW']:,.0f}đ</b> ({cw['price_change_pct']:+.1f}%)\n"
                f"  Đòn bẩy: <b>{cw['F_DonBay']:.1f}x</b> | Đáo hạn: <b>{cw['L_Ngay']} ngày</b>\n"
            )
        msg += "\n"
            
    if buys:
        msg += f"🟢 <b>BUY</b> ({len(buys)} mã)\n"
        for cw in buys:  # Show all BUY
            symbol = html.escape(str(cw['A_MaCW']))
            msg += (
                f"• <b>{symbol}</b> | Điểm: <b>{cw['G_Score']:.1f}</b> | "
                f"Giá: <b>{cw['C_GiaCW']:,.0f}đ</b> ({cw['price_change_pct']:+.1f}%)\n"
                f"  Đòn bẩy: <b>{cw['F_DonBay']:.1f}x</b> | Đáo hạn: <b>{cw['L_Ngay']} ngày</b>\n"
            )
        msg += "\n"
            
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += "<i>Nhấn nút bên dưới để xem chi tiết</i>\n"
    msg += "<b>🤖 Finvista Quant System</b>"
    
    # Create inline keyboard
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "📊 Xem CSV chi tiết", "callback_data": "view_csv"},
                {"text": "📥 Tải báo cáo", "callback_data": "download_report"}
            ],
            [
                {"text": "⚙️ Cài đặt", "callback_data": "settings"},
                {"text": "🔄 Quét lại", "callback_data": "rescan"}
            ]
        ]
    }
    
    # Telegram max message length is 4096 characters.
    # Truncate if necessary, leaving room for the suffix.
    if len(msg) > 4000:
        msg = msg[:4000] + "\n\n... [Danh sách đã được rút gọn do giới hạn độ dài của Telegram] ...\n"
        
    # POST to Telegram API
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": msg,
        "parse_mode": "HTML",
        "reply_markup": keyboard
    }
    
    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code == 200:
            print(f"🚀 [Telegram Alerts] Message successfully pushed to channel {chat_id}!")
        else:
            print(f"⚠️ [Telegram Alerts] Bot returned error code {resp.status_code}: {resp.text}")
    except Exception as e:
        print(f"⚠️ [Telegram Alerts] Connection error while dispatching webhook: {e}")


def generate_financial_commentary(rec: dict) -> str:
    """Generate a high-fidelity Vietnamese financial commentary explaining the root causes of distress."""
    # Try AI-powered commentary first
    try:
        from src.infra.ai_client import get_ai_client
        ai_client = get_ai_client()
        
        commentary = ai_client.generate_financial_commentary(
            ticker=rec.get("ticker", "UNKNOWN"),
            current_ratio=float(rec.get("current_ratio", 1.0) or 1.0),
            debt_ratio=float(rec.get("debt_ratio", 0.5) or 0.5),
            altman_z_score=float(rec.get("altman_z_score", 0.0) or 0.0),
            profit_after_tax=float(rec.get("profit_after_tax", 0.0) or 0.0),
            operating_cash_flow=float(rec.get("operating_cash_flow", 0.0) or 0.0),
            ebit_to_interest=float(rec.get("ebit_to_interest", 9999.0) or 9999.0)
        )
        
        if commentary:
            return commentary
    except Exception as e:
        print(f"⚠️ AI commentary failed, falling back to rule-based: {e}")
    
    # Fallback to rule-based commentary
    c_ratio = float(rec.get("current_ratio", 1.0) or 1.0)
    d_ratio = float(rec.get("debt_ratio", 0.5) or 0.5)
    pat = float(rec.get("profit_after_tax", 0.0) or 0.0)
    ocf = float(rec.get("operating_cash_flow", 0.0) or 0.0)
    icr = float(rec.get("ebit_to_interest", 9999.0) or 9999.0)
    
    reasons = []
    
    # 1. Evaluate short-term solvency
    if c_ratio < 0.5:
        reasons.append("khủng hoảng thanh khoản nghiêm trọng (hệ số thanh toán hiện thời cực thấp dưới 0.5)")
    elif c_ratio < 1.0:
        reasons.append("khả năng thanh toán ngắn hạn yếu (tài sản ngắn hạn không đủ bù đắp nợ ngắn hạn)")
        
    # 2. Evaluate capital structure / leverage
    if d_ratio > 0.8:
        reasons.append("đòn bẩy tài chính cực đoan (nợ chiếm hơn 80% tổng tài sản)")
    elif d_ratio > 0.65:
        reasons.append("tỷ lệ nợ vay cao gây áp lực lớn lên cấu trúc nguồn vốn")
        
    # 3. Evaluate profitability
    if pat < -100000000000 or pat < 0: # negative profit
        reasons.append("hoạt động kinh doanh thua lỗ bào mòn vốn chủ sở hữu")
        
    # 4. Evaluate operational cash flow
    if ocf < 0:
        reasons.append("dòng tiền từ hoạt động sản xuất kinh doanh âm nặng gây thâm hụt ngân quỹ")
        
    # 5. Evaluate interest coverage
    if icr < 1.0:
        reasons.append("lợi nhuận cốt lõi (EBIT) không đủ bù đắp chi phí lãi vay (hệ số ICR dưới 1.0)")

    if not reasons:
        return "Các chỉ số tài chính cơ bản suy yếu kết hợp với điểm số cảnh báo sớm Altman Z'' sụt giảm mạnh."
        
    # Format beautifully
    commentary = "Doanh nghiệp đối mặt với " if d_ratio > 0.65 or c_ratio < 1.0 else "Rủi ro phát sinh từ "
    if len(reasons) == 1:
        commentary += reasons[0] + "."
    elif len(reasons) == 2:
        commentary += f"{reasons[0]} kết hợp {reasons[1]}."
    else:
        commentary += f"{reasons[0]}, {reasons[1]} và {reasons[2]}."
        
    # Capitalize first letter of commentary
    return commentary[0].upper() + commentary[1:]


def send_credit_distress_alert_batch(distressed_records: list):
    """
    Send a beautifully formatted Telegram notification when listed companies 
    are flagged with extreme financial distress or Altman Z-Score fall.
    - Interactive inline keyboard for quick actions
    """
    config = load_telegram_config()
    token = config.get("telegram_bot_token", "").strip()
    chat_id = config.get("telegram_chat_id", "").strip()
    enabled = config.get("enable_alerts", False)
    
    if not enabled or not distressed_records:
        return
        
    if not token or "YOUR_TELEGRAM" in token or not chat_id or "YOUR_TELEGRAM" in chat_id:
        print("\n📢 [Telegram Alerts] Active Credit alerts are ENABLED but credentials are not configured.")
        return
        
    msg = "🚨 <b>[CẢNH BÁO KHỦNG HOẢNG TÍN DỤNG]</b> 🚨\n"
    msg += f"📅 <i>Thời gian quét: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</i>\n"
    msg += "=========================\n\n"
    msg += "⚠️ <b>PHÁT HIỆN DOANH NGHIỆP RƠI VÀO VÙNG NGUY HIỂM (Danger Zone):</b>\n\n"
    
    # Process up to 3 records and keep length under Telegram's limit
    max_records = 3
    for rec in distressed_records[:max_records]:
        ticker = html.escape(str(rec.get("ticker", "UNKNOWN")))
        z_score = float(rec.get("altman_z_score", 0.0) or 0.0)
        prob = float(rec.get("xgboost_distress_probability", 0.0) or 0.0)
        prob_pct = prob * 100
        
        # Generate and truncate commentary safely
        commentary = html.escape(generate_financial_commentary(rec))
        if len(commentary) > 150:
            commentary = commentary[:147] + "..."
            
        entry = (
            f"• <b>Mã CP:</b> <code>{ticker}</code>\n"
            f"  - Hệ số Thanh toán: <b>{rec.get('current_ratio', 0.0):.2f}</b>\n"
            f"  - Nợ/Tổng tài sản: <b>{rec.get('debt_ratio', 0.0)*100:.1f}%</b>\n"
            f"  - Điểm Altman Z'': 📉 <b>{z_score:.2f}</b> (Danger &lt; 1.10)\n"
            f"  - Xác suất Kiệt quệ ML: 🚨 <b>{prob_pct:.1f}%</b>\n"
            f"  - 🔍 <b>Nguyên nhân chính:</b> <i>{commentary}</i>\n"
            f"  - 👉 <b>KHUYẾN NGHỊ: ĐÓNG BĂNG tất cả các Chứng quyền liên quan!</b>\n\n"
        )
        
        if len(msg) + len(entry) + 250 > 4000:
            msg += f"<i>... và {len(distressed_records) - distressed_records.index(rec)} doanh nghiệp khác. Vui lòng tải báo cáo CSV để xem chi tiết.</i>\n\n"
            break
        msg += entry
    else:
        if len(distressed_records) > max_records:
            msg += f"<i>... và {len(distressed_records) - max_records} doanh nghiệp khác. Vui lòng tải báo cáo CSV để xem chi tiết.</i>\n\n"
        
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += "<i>Nhấn nút bên dưới để hành động</i>\n"
    msg += "<b>Finvista Credit Risk System</b>"
    
    # Create inline keyboard
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "📋 Xem danh sách đầy đủ", "callback_data": "view_full_list"},
                {"text": "📥 Tải báo cáo rủi ro", "callback_data": "download_risk_report"}
            ],
            [
                {"text": "🔄 Quét lại ngay", "callback_data": "rescan_credit"},
                {"text": "⚙️ Cài đặt cảnh báo", "callback_data": "alert_settings"}
            ]
        ]
    }
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": msg,
        "parse_mode": "HTML",
        "reply_markup": keyboard
    }
    
    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code == 200:
            print(f"🚀 [Telegram Alerts] Message successfully pushed to channel {chat_id}!")
        else:
            print(f"⚠️ [Telegram Alerts] Bot returned error code {resp.status_code}: {resp.text}")
    except Exception as e:
        print(f"⚠️ [Telegram Alerts] Connection error while dispatching webhook: {e}")


def handle_callback_query(callback_query_id: str, callback_data: str, chat_id: str):
    """
    Handle inline keyboard button callbacks from Telegram.
    This function should be called when a user clicks a button.
    
    Note: To use this, you need to set up a webhook or polling mechanism
    to receive callback queries from Telegram.
    """
    config = load_telegram_config()
    token = config.get("telegram_bot_token", "").strip()
    
    if not token or "YOUR_TELEGRAM" in token:
        print("⚠️ Telegram bot token not configured")
        return
    
    # Process different callback actions
    response_text = ""
    alert = False  # Whether to show a notification to the user
    edit_message = None  # Optional: edit the original message
    
    if callback_data == "view_csv":
        response_text = "📊 File CSV đã sẵn sàng! Kiểm tra thư mục data/processed/"
        alert = True
        # Send CSV file if it exists
        try:
            from src.core import config
            csv_path = config.CLEANED_FINANCIALS_FILE
            if os.path.exists(csv_path):
                send_document(chat_id, csv_path, "Báo cáo CSV chi tiết")
        except Exception as e:
            print(f"⚠️ Error sending CSV: {e}")
            
    elif callback_data == "download_report":
        response_text = "📥 Đang chuẩn bị báo cáo Excel..."
        alert = True
        try:
            from src.core import config
            excel_path = os.path.join("data", "processed", "excel_cw_report.csv")
            if os.path.exists(excel_path):
                send_document(chat_id, excel_path, "Báo cáo Excel")
        except Exception as e:
            print(f"⚠️ Error sending report: {e}")
            
    elif callback_data == "settings":
        response_text = "⚙️ Cài đặt chưa được implement"
        alert = True
        
    elif callback_data == "rescan":
        response_text = "🔄 Đang quét lại thị trường..."
        alert = True
        # Trigger rescan (you can call your analysis script here)
        try:
            import subprocess
            subprocess.Popen(["python", "scripts/run_cw.py", "--all"])
        except Exception as e:
            print(f"⚠️ Error triggering rescan: {e}")
            
    elif callback_data == "view_full_list":
        response_text = "📋 Đang tải danh sách đầy đủ..."
        alert = True
        # Send full list as file or message
        try:
            from src.core import config
            csv_path = config.FINAL_DATASET_FILE
            if os.path.exists(csv_path):
                send_document(chat_id, csv_path, "Danh sách đầy đủ")
        except Exception as e:
            print(f"⚠️ Error sending full list: {e}")
            
    elif callback_data == "download_risk_report":
        response_text = "📥 Đang tải báo cáo rủi ro..."
        alert = True
        try:
            from src.core import config
            report_path = os.path.join(config.PROCESSED_DATA_DIR, "data_quality_report.json")
            if os.path.exists(report_path):
                send_document(chat_id, report_path, "Báo cáo rủi ro tín dụng")
        except Exception as e:
            print(f"⚠️ Error sending risk report: {e}")
            
    elif callback_data == "rescan_credit":
        response_text = "🔄 Đang quét lại rủi ro tín dụng..."
        alert = True
        # Trigger credit pipeline rescan
        try:
            import subprocess
            subprocess.Popen(["python", "run.py", "credit"])
        except Exception as e:
            print(f"⚠️ Error triggering credit rescan: {e}")
            
    elif callback_data == "alert_settings":
        response_text = "⚙️ Cài đặt cảnh báo chưa được implement"
        alert = True
        
    else:
        response_text = "❌ Hành động không được hỗ trợ"
        alert = True
    
    # Answer the callback query
    url = f"https://api.telegram.org/bot{token}/answerCallbackQuery"
    payload = {
        "callback_query_id": callback_query_id,
        "text": response_text,
        "show_alert": alert
    }
    
    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code == 200:
            print(f"✅ Callback handled: {callback_data}")
        else:
            print(f"⚠️ Callback error: {resp.status_code}")
    except Exception as e:
        print(f"⚠️ Callback handling error: {e}")


def send_document(chat_id: str, file_path: str, caption: str = ""):
    """Send a document/file to Telegram chat"""
    config = load_telegram_config()
    token = config.get("telegram_bot_token", "").strip()
    
    if not token or "YOUR_TELEGRAM" in token:
        print("⚠️ Telegram bot token not configured")
        return
    
    url = f"https://api.telegram.org/bot{token}/sendDocument"
    
    try:
        with open(file_path, 'rb') as f:
            files = {'document': f}
            data = {
                'chat_id': chat_id,
                'caption': caption
            }
            resp = requests.post(url, files=files, data=data, timeout=30)
            if resp.status_code == 200:
                print(f"✅ Document sent successfully: {file_path}")
            else:
                print(f"⚠️ Document send error: {resp.status_code}")
    except Exception as e:
        print(f"⚠️ Error sending document: {e}")
