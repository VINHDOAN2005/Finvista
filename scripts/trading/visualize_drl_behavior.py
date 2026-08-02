# -*- coding: utf-8 -*-
"""
🎨 FINVISTA: DRL BEHAVIOR VISUALIZER (ASCII)
===========================================
Generates a text-based visual representation of how the DRL Agent
allocates capital between Stocks and Cash over time.

Author: samvo
"""

import pandas as pd
import numpy as np
import os
import sys

# Ensure project root is in path
sys.path.append(os.getcwd())

from scripts.trading.evaluate_drl_real_data import prepare_real_data
from src.modules.regime_analysis.portfolio.drl_portfolio_agent import DRLPortfolioAgent, VNWarrantEnv

def generate_ascii_area_chart(data: pd.DataFrame, title: str, width: int = 80, height: int = 15):
    """
    Generates an ASCII area chart for portfolio allocation.
    data: DataFrame with index as Date and columns as Asset Weights.
    """
    print("\n" + "=" * width)
    print(f" {title.center(width - 2)} ")
    print("=" * width)
    
    # We want to show the 'CASH' portion vs 'STOCKS' portion
    # Assume the last column is CASH
    cash_col = data.columns[-1]
    stocks_sum = data.iloc[:, :-1].sum(axis=1)
    cash_val = data[cash_col]
    
    # Resample to fit width
    if len(data) > width:
        indices = np.linspace(0, len(data) - 1, width).astype(int)
        plot_stocks = stocks_sum.iloc[indices].values
        plot_cash = cash_val.iloc[indices].values
        dates = data.index[indices]
    else:
        plot_stocks = stocks_sum.values
        plot_cash = cash_val.values
        dates = data.index

    # Render grid
    for h in range(height, 0, -1):
        threshold = h / height
        row = f"{int(threshold*100):>3}% |"
        for i in range(len(plot_stocks)):
            # If threshold is below the stock weight, it's a stock area
            if plot_stocks[i] >= threshold:
                row += "█" # Stock
            # If threshold is above stock weight but below 100%, it's the cash area
            elif (plot_stocks[i] + plot_cash[i]) >= threshold:
                row += "░" # Cash
            else:
                row += " "
        print(row)
    
    print("     " + "-" * len(plot_stocks))
    print("     " + f"{dates[0].date()} {'Timeline (Stocks: █, Cash: ░)'.center(len(plot_stocks)-22)} {dates[-1].date()}")
    print("=" * width + "\n")

def visualize_behavior():
    returns = prepare_real_data()
    n_stocks = len(returns.columns)
    n_assets = n_stocks + 1
    
    vol = returns.rolling(window=20).std().mean(axis=1).fillna(0.01)
    regime_probs = pd.Series(np.clip(vol / vol.max(), 0.1, 0.9), index=returns.index)
    
    env = VNWarrantEnv(returns, regime_probs)
    agent = DRLPortfolioAgent(state_dim=1 + 6*n_stocks + n_assets, action_dim=n_assets)
    
    print("  🧠 Đang huấn luyện Agent (Vui lòng chờ)...")
    agent.train_agent(env, episodes=100)
    
    print("  📈 Đang mô phỏng và phân tích hình dáng phân bổ...")
    state = env.reset()
    done = False
    weights_history = []
    
    while not done:
        weights, _ = agent.select_action(state, evaluate=True)
        weights_history.append(weights)
        state, _, done, _ = env.step(weights)
        
    df_weights = pd.DataFrame(weights_history, index=returns.index[:-1], columns=env.asset_names)
    
    # 1. Toàn bộ quá trình
    generate_ascii_area_chart(df_weights, "HÌNH DÁNG PHÂN BỔ TÀI SẢN (STOCKS VS CASH) - TOÀN KỲ")
    
    # 2. Zoom vào giai đoạn sập (như đã phân tích ở turn trước)
    df_hist = pd.DataFrame({"bah_ret": returns.mean(axis=1)})
    df_hist["bah_20d_ret"] = df_hist["bah_ret"].rolling(window=20).sum()
    crisis_end_date = df_hist["bah_20d_ret"].idxmin()
    crisis_start_date = crisis_end_date - pd.Timedelta(days=40)
    
    zoom_weights = df_weights.loc[crisis_start_date:crisis_end_date]
    if not zoom_weights.empty:
        generate_ascii_area_chart(zoom_weights, f"CHI TIẾT PHÒNG THỦ TRONG KHỦNG HOẢNG ({crisis_start_date.date()} -> {crisis_end_date.date()})", width=60)

if __name__ == "__main__":
    visualize_behavior()
