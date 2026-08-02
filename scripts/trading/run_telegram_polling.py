# -*- coding: utf-8 -*-
"""
🚀 FINVISTA TELEGRAM POLLING BOT (Local Runner)
==============================================
Chạy Bot trực tiếp trên máy để nhận lệnh /all, /scan, /mã...
Không cần cấu hình Webhook hay Domain.
"""

import time
import requests
import sys
import os

# Thêm thư mục gốc vào path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.infra.telegram_alerts import load_telegram_config, handle_telegram_command

def main():
    config = load_telegram_config()
    token = config.get("telegram_bot_token", "").strip()
    
    if not token or "YOUR_TELEGRAM" in token:
        print("❌ LỖI: Bạn chưa cấu hình Telegram Bot Token trong data/config/telegram_config.json")
        return

    print("=" * 60)
    print("🤖 FINVISTA INTERACTIVE BOT ĐANG CHẠY (Chế độ Polling)...")
    print(f"📡 Đang lắng nghe lệnh từ Telegram...")
    print("💡 Thử gõ /all hoặc /HPG trong Telegram của bạn.")
    print("🛑 Bấm Ctrl + C để dừng Bot.")
    print("=" * 60)

    last_update_id = 0
    url = f"https://api.telegram.org/bot{token}/getUpdates"

    try:
        while True:
            try:
                # Lấy tin nhắn mới
                params = {"offset": last_update_id + 1, "timeout": 30}
                resp = requests.get(url, params=params, timeout=35).json()

                if not resp.get("ok"):
                    print(f"⚠️ Telegram API Error: {resp.get('description')}")
                    time.sleep(5)
                    continue

                for update in resp.get("result", []):
                    last_update_id = update["update_id"]
                    
                    if "message" in update:
                        msg = update["message"]
                        chat_id = msg.get("chat", {}).get("id")
                        text = msg.get("text", "")
                        
                        if text:
                            print(f"📩 Nhận lệnh: {text} từ Chat ID: {chat_id}")
                            # Xử lý lệnh
                            handle_telegram_command(text, str(chat_id))
                    
                    elif "callback_query" in update:
                        # Xử lý nút bấm (nếu có)
                        from src.infra.telegram_alerts import handle_callback_query
                        cb = update["callback_query"]
                        handle_callback_query(cb["id"], cb["data"], str(cb["from"]["id"]))

            except requests.exceptions.RequestException as e:
                print(f"🌐 Lỗi kết nối (Thử lại sau 5s): {e}")
                time.sleep(5)
            except Exception as e:
                print(f"❌ Lỗi không xác định: {e}")
                time.sleep(1)
                
    except KeyboardInterrupt:
        print("\n👋 Bot đã dừng. Hẹn gặp lại!")

if __name__ == "__main__":
    main()
