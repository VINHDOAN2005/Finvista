# -*- coding: utf-8 -*-
import pandas as pd
import matplotlib.pyplot as plt
import os
from src.core.database import engine
from src.modules.credit_risk.models.merton_engine import calculate_merton_dd_realtime

def visualize_merton_risk():
    # 1. Thu thập dữ liệu
    query = "SELECT DISTINCT ticker as symbol FROM company_financials"
    companies = pd.read_sql(query, engine)
    
    results = []
    for ticker in companies['symbol'].unique():
        p_query = f"SELECT close FROM stock_history WHERE symbol = '{ticker}' ORDER BY date DESC LIMIT 1"
        p_df = pd.read_sql(p_query, engine)
        if not p_df.empty:
            merton = calculate_merton_dd_realtime(ticker, p_df['close'].iloc[0])
            if merton.get('status') not in ['insufficient_data', 'error']:
                results.append(merton)
    
    df = pd.DataFrame(results).sort_values('merton_dd', ascending=True)
    
    # 2. Vẽ biểu đồ
    plt.figure(figsize=(12, 8))
    
    # Định nghĩa màu sắc dựa trên DD
    colors = []
    for dd in df['merton_dd']:
        if dd < 2.0: colors.append('#ff4d4d') # Đỏ
        elif dd < 4.0: colors.append('#ffa64d') # Cam
        else: colors.append('#4dff88') # Xanh
        
    bars = plt.bar(df['ticker'], df['merton_dd'], color=colors, edgecolor='black', alpha=0.8)
    
    # Thêm đường ngưỡng cảnh báo
    plt.axhline(y=1.5, color='red', linestyle='--', label='Ngưỡng vỡ nợ (1.5)')
    plt.axhline(y=2.5, color='orange', linestyle='--', label='Vùng theo dõi (2.5)')
    
    plt.title('BẢN ĐỒ RỦI RO CẤU TRÚC MERTON (DISTANCE TO DEFAULT)', fontsize=14, fontweight='bold')
    plt.ylabel('Khoảng cách tới vỡ nợ (DD)', fontsize=12)
    plt.xlabel('Mã cổ phiếu', fontsize=12)
    plt.xticks(rotation=45)
    plt.legend()
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    
    # Lưu ảnh
    plot_dir = 'docs/plots'
    if not os.path.exists(plot_dir):
        os.makedirs(plot_dir)
        
    save_path = os.path.join(plot_dir, 'merton_risk_map.png')
    plt.tight_layout()
    plt.savefig(save_path)
    print(f"✅ Biểu đồ đã được lưu tại: {save_path}")

if __name__ == "__main__":
    visualize_merton_risk()
