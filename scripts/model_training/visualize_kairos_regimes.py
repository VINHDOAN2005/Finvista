# -*- coding: utf-8 -*-
"""
🎨 FINVISTA: KAIROS 8-STATE REGIME VISUALIZER
============================================
Visualizes the market as 8 distinct regimes based on KAIROS logic.

Author: samvo
"""

import pandas as pd
import numpy as np
import os
import sys

# Ensure project root is in path
sys.path.append(os.getcwd())

from src.modules.regime_analysis.indicators.regime_detector import RegimeDetector
from src.core.database import engine

def visualize_kairos_regimes(symbol: str = "FPT", days: int = 500):
    print(f"🔍 Đang phân tích KAIROS Regimes cho mã {symbol}...")
    
    query = f"SELECT date, close FROM stock_history WHERE symbol='{symbol}' ORDER BY date ASC LIMIT {days}"
    df = pd.read_sql(query, engine)
    
    if df.empty:
        print("❌ Không có dữ liệu.")
        return

    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)
    
    # Calculate 8-state regimes
    res = RegimeDetector.calculate_kairos_regimes(df['close'])
    
    # Color mapping for ASCII
    colors = {
        "S0: Đóng_Băng": "❄️",
        "S1: Nén_Chặt": "🟡",
        "S2: Đầu_Xu_Hướng": "🔵",
        "S3: Xu_Hướng_Mạnh": "🟢",
        "S4: Cao_Trào": "🔴",
        "S5: Hồi_Quy": "🟣",
        "S6: Nhiễu_Động": "⚪",
        "S7: Quét_Thanh_Khoản": "🔥"
    }
    
    # ASCII Visualizer
    width = 100
    print("\n" + "=" * width)
    print(f" 🗺️ KAIROS REGIME MAP: {symbol} (Timeline View) ".center(width))
    print("=" * width)
    
    # Timeline
    timeline = ""
    last_regime = None
    step = max(1, len(res) // width)
    
    indices = np.arange(0, len(res), step)
    for idx in indices:
        regime = res['regime'].iloc[idx]
        timeline += colors.get(regime, " ")
        
    print(timeline)
    print("-" * width)
    print(f"{res.index.min().date()} {'Timeline'.center(width-20)} {res.index.max().date()}")
    print("=" * width)
    
    # Summary Table
    print("\n [CHI TIẾT TRẠNG THÁI HIỆN TẠI]")
    latest = res.iloc[-1]
    print(f" -> Ngày: {res.index[-1].date()}")
    print(f" -> Trạng thái: {colors.get(latest['regime'])} {latest['regime']}")
    print(f" -> Momentum: {latest['momentum']:+.2f}%")
    print(f" -> P_Turbulent: {latest['p_turbulent']:.2%}")
    print(f" -> Volatility (30d): {latest['vol_30']:.2%}")
    
    print("\n [HUYỀN THOẠI KAIROS]")
    for k, v in colors.items():
        count = (res['regime'] == k).sum()
        pct = count / len(res) * 100
        print(f" {v} {k:<20} : {pct:>5.1f}% thời gian")
    print("=" * width + "\n")

if __name__ == "__main__":
    visualize_kairos_regimes("FPT")
