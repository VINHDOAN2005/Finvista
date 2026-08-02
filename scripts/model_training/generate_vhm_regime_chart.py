# -*- coding: utf-8 -*-
"""
🎨 FINVISTA: KAIROS REGIME MAP GENERATOR
========================================
Generates a high-quality regime map chart like Kairos Visualizer.
"""

import pandas as pd
import numpy as np
import os
import sys
import matplotlib.pyplot as plt
import mplfinance as mpf

# Ensure project root is in path
sys.path.append(os.getcwd())

from src.modules.regime_analysis.indicators.regime_detector import RegimeDetector
from src.core.database import engine

def generate_regime_chart(symbol: str = "VHM", days: int = 250):
    print(f"🔍 Đang truy xuất dữ liệu cho {symbol}...")
    
    query = f"SELECT date, open, high, low, close, volume FROM stock_history WHERE symbol='{symbol}' ORDER BY date ASC"
    df = pd.read_sql(query, engine)
    
    if df.empty:
        print(f"❌ Không có dữ liệu cho mã {symbol}.")
        return

    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)
    df = df.tail(days)
    
    print(f"🧠 Đang tính toán KAIROS Regimes v3 (Research Grade)...")
    # Calculate 8-state regimes using full OHLC DataFrame
    res = RegimeDetector.calculate_kairos_regimes(df)
    df['regime'] = res['regime']

    # Color mapping for regimes
    regime_colors = {
        "S0: Đóng_Băng": "#2c3e50",      # Dark Gray
        "S1: Nén_Chặt": "#f1c40f",      # Yellow
        "S2: Đầu_Xu_Hướng": "#3498db",   # Blue
        "S3: Xu_Hướng_Mạnh": "#2ecc71",  # Green
        "S4: Cao_Trào": "#e67e22",      # Orange
        "S5: Hồi_Quy": "#9b59b6",       # Purple
        "S6: Nhiễu_Động": "#95a5a6",    # Gray
        "S7: Quét_Thanh_Khoản": "#e91e63" # Pink
    }

    # Create market colors list for each bar
    colors = [regime_colors.get(r, "#ffffff") for r in df['regime']]
    
    # Custom market colors to use in plot
    # Since we want to color bars individually, we'll use a trick or draw them as separate lines/collections
    # Actually mplfinance supports 'marketcolors' but they are usually based on up/down.
    # To color each bar independently, we can use 'make_addplot' with bars or a line chart with scatter.
    
    # Let's use the line chart style from the reference image (it looks like a line chart with dots or just colored segments)
    # Actually, the image looks like it has vertical bars or candlesticks.
    
    # Create the figure with extra space for legend
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 10), gridspec_kw={'height_ratios': [3, 1]}, facecolor='black')
    
    ax1.set_facecolor('black')
    ax2.set_facecolor('black')
    
    # Calculate Keltner Channels for background context
    ema20 = df['close'].ewm(span=20, adjust=False).mean()
    tr = pd.concat([df['high'] - df['low'], (df['high'] - df['close'].shift()).abs(), (df['low'] - df['close'].shift()).abs()], axis=1).max(axis=1)
    atr20 = tr.rolling(window=20).mean()
    upper_kc = ema20 + (2 * atr20)
    lower_kc = ema20 - (2 * atr20)
    
    # Plot Keltner Channels (subtle)
    ax1.plot(upper_kc.values, color='#444444', linestyle='--', alpha=0.5, label='Keltner Upper (2.0 ATR)')
    ax1.plot(lower_kc.values, color='#444444', linestyle='--', alpha=0.5, label='Keltner Lower (2.0 ATR)')
    ax1.fill_between(range(len(df)), lower_kc, upper_kc, color='#222222', alpha=0.2)

    # Plot price candlesticks with regime colors
    for i in range(len(df)):
        color = colors[i]
        # Draw candlestick wick
        ax1.vlines(i, df['low'].iloc[i], df['high'].iloc[i], color=color, linewidth=1)
        # Body
        open_p = df['open'].iloc[i]
        close_p = df['close'].iloc[i]
        height = abs(close_p - open_p)
        bottom = min(open_p, close_p)
        # Ensure body is visible even on flat days
        rect_height = max(height, (df['high'].iloc[i]-df['low'].iloc[i])*0.1, 10) 
        ax1.add_patch(plt.Rectangle((i - 0.35, bottom), 0.7, rect_height, color=color, alpha=0.9))

    # Legend - Move outside to avoid covering data
    from matplotlib.patches import Patch
    legend_elements = [Patch(facecolor=c, label=k) for k, c in regime_colors.items()]
    # Add Keltner to legend
    legend_elements.append(plt.Line2D([0], [0], color='#444444', linestyle='--', label='Keltner Channel'))
    
    leg = ax1.legend(handles=legend_elements, title="REGIME MAP LEGEND", loc='upper left', 
                     bbox_to_anchor=(1.02, 1), borderaxespad=0,
                     facecolor='black', edgecolor='white', labelcolor='white')
    plt.setp(leg.get_title(), color='white')
    
    ax1.set_title(f"KAIROS Regime Visualizer v2.1 (Optimized) - {symbol}", color='white', fontsize=18, pad=20)
    ax1.tick_params(axis='both', colors='white')
    ax1.grid(color='#333333', linestyle=':', alpha=0.5)
    ax1.set_ylabel("Price (VND)", color='white')
    
    # Volume
    vol_ma20 = df['volume'].rolling(window=20).mean()
    for i in range(len(df)):
        ax2.bar(i, df['volume'].iloc[i], color=colors[i], alpha=0.6)
    
    ax2.plot(vol_ma20.values, color='cyan', linewidth=1.5, alpha=0.8, label='Vol MA 20')
    ax2.legend(loc='upper left', facecolor='black', edgecolor='none', labelcolor='white', fontsize=8)
    
    ax2.tick_params(axis='both', colors='white')
    ax2.grid(color='#333333', linestyle=':', alpha=0.5)
    ax2.set_ylabel("Volume", color='white')
    
    # X-axis labels (Dates)
    n = len(df)
    step = max(1, n // 12)
    indices = np.arange(0, n, step)
    ax2.set_xticks(indices)
    ax2.set_xticklabels([df.index[i].strftime('%d/%m/%y') for i in indices], rotation=0, color='white')
    
    # Adjust layout to make room for legend on the right
    plt.subplots_adjust(right=0.82, left=0.08, top=0.92, bottom=0.1, hspace=0.15)
    
    output_path = f"{symbol.lower()}_regime_map_v2.png"
    plt.savefig(output_path, facecolor='black', dpi=140) # Higher DPI for AI Vision
    print(f"✅ Đã lưu biểu đồ tối ưu tại: {output_path}")
    plt.close()

    # --- NEW: EXPORT DATA FOR AI INGESTION ---
    export_df = df.copy()
    # Add extra metrics for agent context
    export_df['p_turbulent'] = res['p_turbulent']
    export_df['momentum'] = res['momentum']
    export_df['vol_30'] = res['vol_30']
    
    csv_path = f"data/processed/{symbol.lower()}_regime_ingest.csv"
    os.makedirs("data/processed", exist_ok=True)
    export_df.to_csv(csv_path)
    print(f"💾 Đã xuất dữ liệu Ingestion cho Agent tại: {csv_path}")

if __name__ == "__main__":
    symbol = sys.argv[1] if len(sys.argv) > 1 else "VHM"
    generate_regime_chart(symbol)
