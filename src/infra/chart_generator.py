# -*- coding: utf-8 -*-
"""
📸 FINVISTA VISUAL ENGINE
=========================
Tự động truy xuất dữ liệu từ SQLite, render biểu đồ nến chuyên nghiệp (Candlestick)
kèm các chỉ báo kỹ thuật (Volume, EMA) và xuất thẳng ra chuỗi Base64 (trên RAM)
để gửi cho AI (Gemini) phân tích thị giác (Vision).

Author: samvo
"""

import io
import os
import base64
import pandas as pd
import mplfinance as mpf
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

# Setup Database Connection
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_DIR = os.path.join(BASE_DIR, "data")
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{os.path.join(DB_DIR, 'finvista.db')}")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
engine = create_engine(DATABASE_URL)

def generate_candlestick_base64(ticker: str, days: int = 120) -> str:
    """
    Truy vấn dữ liệu lịch sử, vẽ biểu đồ và trả về ảnh định dạng Base64.
    """
    query = f"""
        SELECT date, open, high, low, close, volume
        FROM stock_history
        WHERE symbol = '{ticker}'
        ORDER BY date DESC
        LIMIT {days}
    """
    df = pd.read_sql(query, engine)

    if df.empty:
        raise ValueError(f"❌ Không tìm thấy dữ liệu lịch sử cho mã {ticker} trong Database.")

    # Đảo ngược dữ liệu về đúng trình tự thời gian (cũ -> mới)
    df = df.iloc[::-1].reset_index(drop=True)
    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)

    # Ép kiểu dữ liệu sang float
    cols = ['open', 'high', 'low', 'close', 'volume']
    df[cols] = df[cols].astype(float)

    # Thêm các chỉ báo kỹ thuật: EMA 15 và EMA 50
    ema15 = mpf.make_addplot(df['close'].ewm(span=15, adjust=False).mean(), color='blue', width=1.5)
    ema50 = mpf.make_addplot(df['close'].ewm(span=50, adjust=False).mean(), color='orange', width=1.5)

    # Khởi tạo bộ nhớ đệm RAM để lưu ảnh
    buf = io.BytesIO()

    # Định dạng style biểu đồ nến chuẩn chuyên nghiệp
    mc = mpf.make_marketcolors(up='g', down='r', edge='inherit', wick='inherit', volume='in', ohlc='inherit')
    s = mpf.make_mpf_style(marketcolors=mc, gridstyle=':', y_on_right=True)

    # Render biểu đồ
    mpf.plot(
        df,
        type='candle',
        volume=True,
        addplot=[ema15, ema50],
        style=s,
        title=f"\n{ticker} - {days} Days Technical Chart (EMA15, EMA50)",
        ylabel="Price",
        ylabel_lower="Volume",
        figsize=(10, 6),
        savefig=buf  # Lưu thẳng vào RAM thay vì tạo file cứng
    )

    # Chuyển đổi ảnh sang chuỗi Base64
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    buf.close()

    return img_base64

# ==========================================
# TEST NHANH MODULE NẾU CHẠY TRỰC TIẾP FILE
# ==========================================
if __name__ == "__main__":
    try:
        print("📸 Đang tạo ảnh biểu đồ HPG...")
        b64_img = generate_candlestick_base64("HPG", days=120)
        print(f"✅ Thành công! Chuỗi Base64 (Dài: {len(b64_img)} ký tự).")
        print(f"Bản xem trước Base64: {b64_img[:50]}...{b64_img[-50:]}")
    except Exception as e:
        print(f"Lỗi: {e}")