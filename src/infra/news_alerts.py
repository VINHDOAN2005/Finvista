# -*- coding: utf-8 -*-
"""
🚀 FINVISTA: AI NEWS ALERT DISPATCHER
=====================================
Processes raw corporate news/events from the database, runs AI summarization,
and dispatches high-signal alerts to Telegram.
"""

import os
import html
import requests
from datetime import datetime, timezone
from sqlalchemy import desc
from src.core.database import SessionLocal, CorporateNews, CorporateEvent
from src.infra.telegram_alerts import load_telegram_config
from src.infra.ai_client import get_ai_client
from src.core.utils import logger

def dispatch_news_alerts(limit: int = 5):
    """Fetch latest un-alerted news, summarize with AI, and send to Telegram."""
    db = SessionLocal()
    config = load_telegram_config()
    
    if not config.get("enable_alerts"):
        return

    try:
        # For simplicity, we'll fetch news from the last hour or just the N latest 
        # In a real system, you'd track 'is_alerted' in the DB.
        latest_news = db.query(CorporateNews).order_by(desc(CorporateNews.created_at)).limit(limit).all()
        
        if not latest_news:
            return

        ai_client = get_ai_client()
        token = config.get("telegram_bot_token")
        chat_id = config.get("telegram_chat_id")
        
        for news in latest_news:
            # Simple deduplication: Check if we sent this link recently (optional state file)
            # For now, let's just process the news
            
            summary_prompt = f"""Bạn là Chuyên gia Phân tích Tin tức Tài chính.
Hãy tóm tắt tin tức sau đây thành một thông báo ngắn gọn, hấp dẫn cho nhà đầu tư chứng quyền.
Tiêu đề: {news.title}
Cơ sở/Mã: {news.symbol}
Phân loại: {news.category}

Yêu cầu:
1. Độ dài tối đa 3 câu.
2. Đánh giá tác động (Tích cực/Tiêu cực/Trung lập).
3. Sử dụng emoji phù hợp.
Trả lời bằng tiếng Việt."""

            summary = ai_client.chat([{"role": "user", "content": summary_prompt}], temperature=0.3)
            
            msg = f"📰 <b>TIN TỨC MỚI: {news.symbol}</b>\n"
            msg += f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            msg += f"<b>{html.escape(news.title)}</b>\n\n"
            msg += f"🤖 <b>AI Tóm tắt:</b>\n<i>{html.escape(summary)}</i>\n\n"
            msg += f"🔗 <a href='{news.link}'>Xem chi tiết tại Vietstock</a>\n"
            msg += f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            msg += f"<b>Finvista News Intelligence</b>"

            url = f"https://api.telegram.org/bot{token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": msg,
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            }
            
            requests.post(url, json=payload, timeout=10)
            
    except Exception as e:
        logger.error(f"❌ Error dispatching news alerts: {e}")
    finally:
        db.close()

def dispatch_event_alerts(limit: int = 3):
    """Fetch upcoming corporate events and alert via Telegram."""
    db = SessionLocal()
    config = load_telegram_config()
    
    if not config.get("enable_alerts"):
        return

    try:
        # Fetch events created/updated recently
        latest_events = db.query(CorporateEvent).order_by(desc(CorporateEvent.last_updated)).limit(limit).all()
        
        if not latest_events:
            return

        token = config.get("telegram_bot_token")
        chat_id = config.get("telegram_chat_id")
        
        for ev in latest_events:
            msg = f"📅 <b>SỰ KIỆN DOANH NGHIỆP: {ev.ticker}</b>\n"
            msg += f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            msg += f"🗓 <b>Ngày:</b> {ev.event_date}\n"
            msg += f"🔹 <b>Loại:</b> {ev.event_type}\n"
            msg += f"📝 <b>Nội dung:</b> {html.escape(ev.description)}\n\n"
            msg += f"💡 <i>AI Note: Sự kiện này có thể ảnh hưởng đến định giá chứng quyền liên quan.</i>\n"
            msg += f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            msg += f"<b>Finvista Event Tracker</b>"

            url = f"https://api.telegram.org/bot{token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": msg,
                "parse_mode": "HTML"
            }
            
            requests.post(url, json=payload, timeout=10)
            
    except Exception as e:
        logger.error(f"❌ Error dispatching event alerts: {e}")
    finally:
        db.close()
