# -*- coding: utf-8 -*-
"""
📦 FINVISTA: SMART MARKET DATA CACHE
=====================================
Session-aware caching for CW market data (bid/ask/prices).

Logic:
  - Dữ liệu được cache trong DB (bảng market_data_snapshot)
  - Trước 15 phút mở phiên (< 08:45): dùng cache cuối phiên trước
  - Từ 08:45 đến hết phiên (15:00): fetch live, cập nhật cache mỗi lần scan
  - Sau 15:00: cache data cuối phiên, giữ đến 08:45 ngày hôm sau

Author: samvo
"""

import json
import os
from datetime import datetime, timedelta, time
from typing import Optional

import pandas as pd

# ─── Định nghĩa giờ phiên giao dịch HOSE (giờ Việt Nam, UTC+7) ──────────────
MARKET_OPEN      = time(9, 0)   # 09:00
MARKET_CLOSE     = time(15, 0)  # 15:00
CACHE_RESET_TIME = time(8, 45)  # 15 phút trước khi mở phiên

CACHE_FILE = os.path.join("data", "processed", "market_data_snapshot.json")


def _now_vn() -> datetime:
    """Lấy thời gian hiện tại (UTC+7, Vietnam Standard Time)."""
    return datetime.now()


def get_last_trading_session_date(dt: datetime) -> str:
    """Trả về ngày của phiên giao dịch đóng cửa gần nhất (định dạng YYYY-MM-DD)."""
    current_date = dt.date()
    current_time = dt.time()
    
    # Nếu trong tuần và đã sau 15:00, phiên giao dịch hôm nay đã đóng cửa
    if dt.weekday() < 5 and current_time >= MARKET_CLOSE:
        target_date = current_date
    else:
        # Nếu chưa đóng cửa hoặc là cuối tuần, phiên gần nhất ít nhất là từ ngày hôm trước
        target_date = current_date - timedelta(days=1)
        
    # Bỏ qua ngày cuối tuần
    while target_date.weekday() >= 5:
        target_date -= timedelta(days=1)
        
    return target_date.strftime("%Y-%m-%d")


def is_cache_up_to_date(now: datetime) -> bool:
    """Kiểm tra xem dữ liệu trong cache có khớp với phiên giao dịch gần nhất không."""
    try:
        if not os.path.exists(CACHE_FILE):
            return False
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            snapshot = json.load(f)
        
        cache_session_date = snapshot.get("trading_session_date", "")
        expected_session_date = get_last_trading_session_date(now)
        
        # Nếu ngày session trong cache trùng hoặc mới hơn ngày session mong đợi
        return cache_session_date >= expected_session_date
    except Exception:
        return False


def is_trading_session() -> bool:
    """True nếu đang trong giờ giao dịch HOSE (09:00–15:00 weekdays)."""
    now = _now_vn()
    if now.weekday() >= 5:   # Thứ 7, CN
        return False
    t = now.time()
    return MARKET_OPEN <= t <= MARKET_CLOSE


def should_use_cache() -> bool:
    """
    True nếu nên dùng cache (ngoài giờ giao dịch VÀ trước 08:45 VÀ cache hợp lệ/mới nhất).
    Trong giờ hoặc nếu cache bị cũ: luôn fetch live để cập nhật dữ liệu phiên mới.
    """
    now = _now_vn()
    
    # 1. Kiểm tra xem cache có mới nhất không
    if not is_cache_up_to_date(now):
        # Cache bị cũ hoặc không tồn tại -> Bắt buộc fetch live để lấy giá đóng cửa mới nhất
        return False
        
    # 2. Nếu cache đã mới nhất, áp dụng logic giờ giấc để tránh gọi API dư thừa
    if now.weekday() >= 5:
        return True   # Cuối tuần -> dùng cache
    t = now.time()
    if t >= CACHE_RESET_TIME and t < MARKET_OPEN:
        return False  # 08:45–09:00: bắt đầu reset cache, chuẩn bị phiên mới
    if t >= MARKET_OPEN and t <= MARKET_CLOSE:
        return False  # Đang phiên: luôn fetch live
    return True       # Ngoài giờ (< 08:45 hoặc > 15:00): dùng cache


def save_snapshot(df: pd.DataFrame) -> None:
    """Lưu snapshot dữ liệu market vào file JSON cache."""
    try:
        os.makedirs(os.path.dirname(CACHE_FILE) or ".", exist_ok=True)
        now = _now_vn()
        snapshot = {
            "saved_at": now.isoformat(),
            "trading_session_date": get_last_trading_session_date(now),
            "is_end_of_session": now.time() >= MARKET_CLOSE,
            "record_count": len(df),
            "data": df.to_dict(orient="records")
        }
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, ensure_ascii=False, default=str)
        session_label = "EOD" if snapshot["is_end_of_session"] else "IN-SESSION"
        print(f"   [CACHE] Market cache saved [{session_label}]: {len(df)} tickers at {now.strftime('%H:%M:%S')}")
    except Exception as e:
        print(f"   [CACHE] Cannot save market cache: {e}")


def load_snapshot() -> Optional[pd.DataFrame]:
    """
    Load cache từ file JSON. Trả về dữ liệu cache nếu tồn tại
    mà không giới hạn thời gian lưu (hỗ trợ load dữ liệu cuối phiên cũ khi ngoài phiên).
    """
    try:
        if not os.path.exists(CACHE_FILE):
            return None
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            snapshot = json.load(f)

        saved_at_str = snapshot.get("saved_at", "")
        saved_at = datetime.fromisoformat(saved_at_str)
        now = _now_vn()

        records = snapshot.get("data", [])
        if records:
            df = pd.DataFrame(records)
            age_mins = (now - saved_at).total_seconds() / 60
            date_label = saved_at.strftime("%d/%m/%Y %H:%M")
            print(f"   [CACHE] Market cache loaded: {len(df)} symbols (Saved: {date_label}, {age_mins:.0f} mins ago)")
            return df
    except Exception as e:
        print(f"   [CACHE] Error reading market cache: {e}")
    return None


def get_session_status() -> dict:
    """Trả về trạng thái phiên giao dịch hiện tại."""
    now = _now_vn()
    t = now.time()
    if now.weekday() >= 5:
        status = "CUỐI TUẦN"
    elif t < CACHE_RESET_TIME:
        status = "TRƯỚC PHIÊN (DÙNG CACHE)"
    elif t < MARKET_OPEN:
        status = "RESET CACHE (08:45–09:00)"
    elif t <= MARKET_CLOSE:
        status = "ĐANG GIAO DỊCH (LIVE)"
    else:
        status = "SAU PHIÊN (LƯU CACHE)"
    return {
        "now": now.isoformat(),
        "status": status,
        "is_trading": is_trading_session(),
        "use_cache": should_use_cache(),
        "cache_file": CACHE_FILE,
        "cache_exists": os.path.exists(CACHE_FILE),
    }
