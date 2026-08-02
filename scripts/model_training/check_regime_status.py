# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
import sys
import os

# Ensure project root is in path
sys.path.append(os.getcwd())

from src.modules.regime_analysis.indicators.regime_detector import RegimeDetector
from src.core.database import engine

def check_current_regime():
    print("🔍 Đang phân tích trạng thái thị trường (Regime Detection)...")
    
    # Lấy dữ liệu VNINDEX hoặc FPT làm đại diện thị trường
    query = "SELECT date, close FROM stock_history WHERE symbol='FPT' ORDER BY date ASC"
    df = pd.read_sql(query, engine)
    
    if df.empty:
        print("❌ Không có dữ liệu để phân tích.")
        return

    returns = df['close'].pct_change().fillna(0).values
    
    # Khởi tạo bộ dò Regime (Hamilton Markov Switching)
    rd = RegimeDetector()
    hm = rd.HamiltonMarkovSwitching()
    
    # Fit mô hình
    hm.fit(returns)
    
    # Dự báo xác suất trạng thái hiện tại
    probs = hm.predict_probs(returns)
    current_prob = probs[-1]
    latest_date = df['date'].iloc[-1]
    
    print("\n" + "=" * 60)
    print(f" 📊 BÁO CÁO TRẠNG THÁI THỊ TRƯỜNG (REGIME REPORT)")
    print("=" * 60)
    print(f" Ngày cập nhật: {latest_date}")
    print(f" Chỉ số đại diện: FPT (Bluechip VN30)")
    print("-" * 60)
    
    status = "🚨 TURBULENT (BIẾN ĐỘNG MẠNH / RỦI RO)" if current_prob > 0.5 else "✅ NORMAL (ỔN ĐỊNH / AN TOÀN)"
    color_code = "🔴" if current_prob > 0.5 else "🟢"
    
    print(f" Trạng thái hiện tại: {color_code} {status}")
    print(f" Xác suất rủi ro (P_Turbulent): {current_prob:.2%}")
    
    # Giải thích Vĩ mô & Vi mô
    print("\n [Vĩ mô (Macro)]")
    if current_prob > 0.7:
        print(" -> Thị trường đang trong pha 'Structural Break' (Gãy cấu trúc).")
        print(" -> Áp lực bán tháo hoặc biến động chính sách đang chiếm ưu thế.")
    else:
        print(" -> Cấu trúc thị trường duy trì ổn định.")
        print(" -> Dòng tiền vĩ mô chưa có dấu hiệu rút chạy hoảng loạn.")
        
    print("\n [Vi mô (Micro)]")
    vol_30d = np.std(returns[-30:]) * np.sqrt(252)
    print(f" -> Biến động thực tế (30d Vol): {vol_30d:.2%}")
    if vol_30d > 0.35:
        print(" -> Cảnh báo: Biến động vi mô ở mức cao, rủi ro cá biệt lớn.")
    else:
        print(" -> Biến động vi mô ở mức kiểm soát được.")
    
    print("=" * 60 + "\n")

if __name__ == "__main__":
    check_current_regime()
