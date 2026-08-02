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
from datetime import datetime

CONFIG_PATH = os.path.join("data", "telegram_config.json")

def load_telegram_config() -> dict:
    """Load Telegram token, chat ID, and active status from configuration registry."""
    os.makedirs("data", exist_ok=True)
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

def send_telegram_alert_batch(warrants_strong_buy: list, warrants_near_expiry: list):
    """
    Send a beautifully formatted, consolidated HTML alert message containing:
    - Elite quantitative picks (STRONG BUY warrants)
    - Crucial Greek warnings (Days to Expiry < 14 days, highlighting Theta decay)
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
        
    if not warrants_strong_buy and not warrants_near_expiry:
        print("💡 [Telegram Alerts] No alerts triggered (0 STRONG BUY and 0 Warrants < 14 days to expiry). Chat is kept clean.")
        return
        
    # Construct premium HTML message layout
    msg = "🚀 <b>[FINVISTA QUANT COVERED WARRANT ALERTS]</b> 🚀\n"
    msg += f"📅 <i>Thời gian: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</i>\n"
    msg += "=========================\n\n"
    
    if warrants_strong_buy:
        msg += "🔥 <b>CƠ HỘI ĐẦU TƯ CỰC MẠNH (STRONG BUY):</b>\n"
        for cw in warrants_strong_buy[:5]:  # Limit top 5 to keep the message clean and avoid overflow
            msg += (
                f"• <b>Mã CW:</b> <code>{cw['A_MaCW']}</code> ({cw['issuer']})\n"
                f"  - Cổ phiếu cơ sở: <b>{cw['B_MaCPCS']}</b>\n"
                f"  - Thị giá CW: <b>{cw['C_GiaCW']:,.0f}đ</b> ({cw['price_change_pct']:+.1f}%)\n"
                f"  - Volatility Arbitrage: <b>IV {cw['S_IV_Pct']:.1f}%</b> vs <b>HV {cw['S_HV_Pct']:.1f}%</b> (<b>{cw['IV_vs_HV_Signal']}</b>)\n"
                f"  - Hòa vốn: <b>{cw['M_GiaHL']:,.0f}đ</b> | Premium: <b>{cw['Premium_Pct']:+.1f}%</b>\n"
                f"  - Đòn bẩy: <b>{cw['F_DonBay']:.1f}x</b> | Đáo Hạn: <b>{cw['L_Ngay']} ngày</b>\n"
                f"  - Điểm Xếp Hạng: 🌟 <b>{cw['G_Score']:.1f}/100</b>\n\n"
            )
        if len(warrants_strong_buy) > 5:
            msg += f"<i>... và {len(warrants_strong_buy) - 5} mã STRONG BUY khác. Xem chi tiết báo cáo CSV!</i>\n\n"
            
    if warrants_near_expiry:
        msg += "🚨 <b>CẢNH BÁO RỦI RO: CHỨNG QUYỀN SẮP ĐÁO HẠN (&lt; 14 ngày):</b>\n"
        for cw in warrants_near_expiry[:5]:
            msg += (
                f"• <b>Mã CW:</b> <code>{cw['A_MaCW']}</code> ({cw['issuer']})\n"
                f"  - Cổ phiếu cơ sở: <b>{cw['B_MaCPCS']}</b>\n"
                f"  - Thị giá CW: <b>{cw['C_GiaCW']:,.0f}đ</b> | Ngày còn lại: 🚨 <b>{cw['L_Ngay']} ngày</b>\n"
                f"  - Hao mòn Theta: 📉 <b>{cw['T_Theta']:+.0f}đ/ngày</b>\n"
                f"  - Khuyến nghị hiện tại: <b>{cw['U_Signal']}</b>\n\n"
            )
        if len(warrants_near_expiry) > 5:
            msg += f"<i>... và {len(warrants_near_expiry) - 5} mã sắp đáo hạn khác. Hạn chế nắm giữ lâu!</i>\n\n"
            
    msg += "=========================\n"
    msg += "<i>Chúc quý nhà đầu tư giao dịch thành công!</i>\n"
    msg += "🛡️ <b>Hệ thống Phân Tích Định Lượng Finvista</b>"
    
    # POST to Telegram API
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": msg,
        "parse_mode": "HTML"
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
        
    msg = "🚨 <b>[CẢNH BÁO FINVISTA - KHỦNG HOẢNG TÍN DỤNG]</b> 🚨\n"
    msg += f"📅 <i>Thời gian quét: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</i>\n"
    msg += "=========================\n\n"
    msg += "⚠️ <b>PHÁT HIỆN DOANH NGHIỆP RƠI VÀO VÙNG NGUY HIỂM (Danger Zone):</b>\n\n"
    
    for rec in distressed_records[:5]:  # Limit top 5 to keep message neat
        ticker = rec.get("ticker", "UNKNOWN")
        z_score = float(rec.get("altman_z_score", 0.0) or 0.0)
        prob = float(rec.get("xgboost_distress_probability", 0.0) or 0.0)
        prob_pct = prob * 100
        
        # Generate dynamic natural language commentary explanation
        commentary = generate_financial_commentary(rec)
        
        msg += (
            f"• <b>Mã CP:</b> <code>{ticker}</code>\n"
            f"  - Hệ số Thanh toán: <b>{rec.get('current_ratio', 0.0):.2f}</b>\n"
            f"  - Nợ/Tổng tài sản: <b>{rec.get('debt_ratio', 0.0)*100:.1f}%</b>\n"
            f"  - Điểm Altman Z'': 💥 <b>{z_score:.2f}</b> (Danger &lt; 1.10)\n"
            f"  - Xác suất Kiệt quệ ML: 🚨 <b>{prob_pct:.1f}%</b>\n"
            f"  - 🔍 <b>Nguyên nhân chính:</b> <i>{commentary}</i>\n"
            f"  - 👉 <b>KHUYẾN NGHỊ: ĐÓNG BĂNG tất cả các Chứng quyền liên quan!</b>\n\n"
        )
        
    if len(distressed_records) > 5:
        msg += f"<i>... và {len(distressed_records) - 5} mã nguy hiểm khác đã bị loại khỏi rổ an toàn.</i>\n\n"
        
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += "🛡️ <b>Hệ thống Quản Trị Rủi Ro Finvista Credit Risk</b>"
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": msg,
        "parse_mode": "HTML"
    }
    
    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code == 200:
            print(f"🚀 [Telegram Alerts] Message successfully pushed to channel {chat_id}!")
        else:
            print(f"⚠️ [Telegram Alerts] Bot returned error code {resp.status_code}: {resp.text}")
    except Exception as e:
        print(f"⚠️ [Telegram Alerts] Connection error while dispatching webhook: {e}")
