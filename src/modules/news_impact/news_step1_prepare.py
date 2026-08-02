# -*- coding: utf-8 -*-
"""
📊 NEWS STEP 1: PREPARE AND FILTER EVENTS (WITH AI SENTIMENT)
=============================================================
Queries corporate news from the database, normalizes the date,
classifies news sentiment using Gemini AI (with JSON caching and rule-based fallback),
and filters by symbol, keyword, or sentiment.
"""

import os
import json
import socket
import pandas as pd
from sqlalchemy.orm import Session
from src.core.database import CorporateNews
from src.core.utils import logger
from src.infra.ai_client import get_ai_client

CACHE_DIR = os.path.join("data", "processed")
CACHE_FILE = os.path.join(CACHE_DIR, "news_sentiment_cache.json")

def load_sentiment_cache() -> dict:
    """Load news sentiment cache from file."""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"⚠️ Failed to load sentiment cache: {e}")
    return {}

def save_sentiment_cache(cache: dict) -> None:
    """Save news sentiment cache to file."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"⚠️ Failed to save sentiment cache: {e}")

def rule_based_sentiment(title: str, summary: str) -> str:
    """Fallback rule-based sentiment classifier."""
    text = (title + " " + summary).lower()
    
    positive_words = [
        "tăng trưởng", "vượt kế hoạch", "lợi nhuận tăng", "cổ tức", "chia cổ tức", 
        "thành công", "ký kết", "hợp tác", "đạt kỷ lục", "khả quan", "mua lại", 
        "phát hành thêm", "tích cực", "bứt phá", "đột biến", "lãi ròng", "doanh thu tăng"
    ]
    negative_words = [
        "thua lỗ", "sụt giảm", "giảm sâu", "bị phạt", "cảnh báo", "vi phạm", 
        "hủy niêm yết", "tạm ngừng", "khoản phạt", "kiện tụng", "tranh chấp", 
        "tiêu cực", "rủi ro", "nợ xấu", "giảm lợi nhuận", "bất lợi", "triệu tập"
    ]
    
    # Simple count
    pos_count = sum(1 for w in positive_words if w in text)
    neg_count = sum(1 for w in negative_words if w in text)
    
    if pos_count > neg_count:
        return "POSITIVE"
    elif neg_count > pos_count:
        return "NEGATIVE"
    return "NEUTRAL"

def check_proxy_online() -> bool:
    """Fast check if the AI proxy port is open."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.2)
            return s.connect_ex(('localhost', 8081)) == 0
    except Exception:
        return False

def classify_sentiment(news_id: int, title: str, summary: str, cache: dict, is_ai_online: bool) -> str:
    """Classify news sentiment using Gemini AI with fallback."""
    news_id_str = str(news_id)
    if news_id_str in cache:
        return cache[news_id_str]
        
    if not is_ai_online:
        sentiment = rule_based_sentiment(title, summary)
        cache[news_id_str] = sentiment
        return sentiment
        
    # Attempt AI classification
    try:
        ai_client = get_ai_client()
        prompt = (
            "Bạn là một chuyên gia phân tích tài chính định lượng chuyên nghiệp. "
            "Hãy đọc tiêu đề và nội dung tin tức doanh nghiệp dưới đây và phân loại sắc thái cảm xúc đối với giá cổ phiếu.\n"
            "Chỉ trả về duy nhất 1 từ tiếng Anh viết hoa: POSITIVE (Tích cực), NEGATIVE (Tiêu cực), hoặc NEUTRAL (Trung lập).\n"
            "Không thêm bất kỳ giải thích hay ký tự nào khác.\n\n"
            f"Tiêu đề: {title}\n"
            f"Tóm tắt: {summary}"
        )
        
        response = ai_client.chat([{"role": "user", "content": prompt}])
        sentiment = response.strip().upper() if response else ""
        
        # Clean response
        for choice in ["POSITIVE", "NEGATIVE", "NEUTRAL"]:
            if choice in sentiment:
                sentiment = choice
                break
                
        if sentiment not in ["POSITIVE", "NEGATIVE", "NEUTRAL"]:
            raise ValueError(f"Invalid AI response: {response}")
            
    except Exception as e:
        logger.debug(f"AI Sentiment analysis failed for news {news_id}: {e}. Falling back to Rule-based.")
        sentiment = rule_based_sentiment(title, summary)
        
    cache[news_id_str] = sentiment
    return sentiment

def prepare_news_events(
    db: Session, 
    symbol: str = None, 
    keyword: str = None,
    sentiment_filter: str = None
) -> pd.DataFrame:
    """
    Fetch news from DB, classify sentiment (AI with cache/fallback), and apply filters.
    """
    logger.info("🎬 [Step 1] Loading and classifying corporate news events...")
    
    query = db.query(CorporateNews)
    if symbol:
        symbol_upper = symbol.upper().strip()
        query = query.filter(CorporateNews.symbol == symbol_upper)
        logger.info(f"🔍 Filtering news for symbol: {symbol_upper}")
        
    all_news = query.all()
    if not all_news:
        logger.warning("⚠️ No news records found in the database matching symbol filter.")
        return pd.DataFrame()
        
    cache = load_sentiment_cache()
    events = []
    
    # Initialize AI client to auto-start proxy if needed
    try:
        get_ai_client()
    except Exception as e:
        logger.debug(f"Could not auto-start AI client: {e}")
        
    is_ai_online = check_proxy_online()
    if not is_ai_online:
        logger.info("ℹ️ Gemini AI Proxy is offline. Using fast rule-based sentiment classification fallback.")
    else:
        logger.info("🚀 Gemini AI Proxy is online. Using AI sentiment analysis.")
        
    # Process news and classify sentiment
    for idx, item in enumerate(all_news):
        date_str = item.date.strip() if item.date else ""
        if not date_str:
            continue
            
        try:
            parsed_date = pd.to_datetime(date_str, format="%Y-%m-%d %H:%M", errors="coerce")
            if pd.isna(parsed_date):
                parsed_date = pd.to_datetime(date_str.split(" ")[0], format="%Y-%m-%d", errors="coerce")
            if pd.isna(parsed_date):
                continue
        except Exception:
            continue
            
        # Classify sentiment (uses cache if available)
        sent = classify_sentiment(item.id, item.title, item.summary or "", cache, is_ai_online)
        
        events.append({
            "id": item.id,
            "symbol": item.symbol,
            "title": item.title,
            "summary": item.summary or "",
            "date": parsed_date,
            "category": item.category or "Unknown",
            "sentiment": sent
        })
        
        # Periodically save cache
        if idx > 0 and idx % 5 == 0:
            save_sentiment_cache(cache)
            
    save_sentiment_cache(cache)
    
    df = pd.DataFrame(events)
    if df.empty:
        return df
        
    # Apply keyword filter
    if keyword:
        keyword_lower = keyword.lower().strip()
        mask = df["title"].str.lower().str.contains(keyword_lower) | df["summary"].str.lower().str.contains(keyword_lower)
        df = df[mask]
        logger.info(f"🔍 Filtering news by keyword: '{keyword_lower}' (Found {len(df)} matches)")
        
    # Apply sentiment filter
    if sentiment_filter:
        sent_upper = sentiment_filter.upper().strip()
        df = df[df["sentiment"] == sent_upper]
        logger.info(f"🔍 Filtering news by sentiment: '{sent_upper}' (Found {len(df)} matches)")
        
    logger.info(f"✅ [Step 1] Prepared {len(df)} total news events.")
    return df
