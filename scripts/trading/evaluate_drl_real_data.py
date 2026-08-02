# -*- coding: utf-8 -*-
"""
🚀 FINVISTA: PRACTICAL DRL EVALUATION (REAL MARKET DATA)
======================================================
Testing the Kalman-enhanced DRL agent on actual VN30 stock history
fetched from the local database.

Author: samvo
"""

import pandas as pd
import numpy as np
import os
import sys

# Ensure project root is in path
sys.path.append(os.getcwd())

from src.modules.cw_pricing.backtest.opt_cw_backtest_audit import get_all_data
from src.modules.regime_analysis.portfolio.drl_portfolio_agent import DRLPortfolioAgent, VNWarrantEnv, calculate_performance_metrics
from src.modules.regime_analysis.indicators.hmm_regime import GaussianHMM

def prepare_real_data():
    """Fetches real stock returns directly from the stock_history table."""
    print("  📡 Đang lấy dữ liệu thực tế từ table 'stock_history'...")
    from src.core.database import engine
    
    query = """
        SELECT symbol, date, close 
        FROM stock_history 
        WHERE symbol IN ('HPG', 'FPT', 'ACB', 'VHM', 'VIC', 'VNM', 'TCB')
        ORDER BY date ASC
    """
    df = pd.read_sql(query, engine)
    
    if df.empty:
        print("  ⚠️ Không có dữ liệu trong database.")
        return pd.DataFrame()

    # Pivot to get stock close prices
    df['date'] = pd.to_datetime(df['date'])
    prices = df.pivot_table(index='date', columns='symbol', values='close')
    
    # Fill missing values
    prices = prices.ffill().dropna(axis=1, how='all').dropna()
    
    # Calculate daily returns
    returns = prices.pct_change().dropna()
    
    print(f"  ✅ Đã chuẩn bị dữ liệu cho {len(returns.columns)} mã: {list(returns.columns)}")
    print(f"  📊 Khoảng thời gian: {returns.index.min()} -> {returns.index.max()} ({len(returns)} phiên)")
    return returns

def run_practical_evaluation():
    """Runs the DRL-Break vs Benchmarks on real data."""
    returns = prepare_real_data()
    n_assets = len(returns.columns)
    
    # 1. Simple Regime Probabilities (based on VNINDEX volatility or average vol)
    # We use a 20-day rolling vol as a proxy for regime
    vol = returns.rolling(window=20).std().mean(axis=1).fillna(0.01)
    regime_probs = pd.Series(np.clip(vol / vol.max(), 0.1, 0.9), index=returns.index)
    
    # 2. Environments
    env_break = VNWarrantEnv(returns, regime_probs)
    env_bah = VNWarrantEnv(returns, regime_probs) # Buy & Hold
    
    # 3. Initialize & Train Agent (Short training for demo)
    print(f"  🧠 Đang huấn luyện DRL Agent (Kalman + Cash Support) trên dữ liệu thực tế...")
    n_total_assets = n_assets + 1
    agent = DRLPortfolioAgent(state_dim=1 + 6*n_assets + n_total_assets, action_dim=n_total_assets)
    agent.train_agent(env_break, episodes=100)
    
    # 4. Evaluate DRL-Break
    print("  📈 Đang chạy mô phỏng giao dịch...")
    state = env_break.reset()
    done = False
    while not done:
        weights, _ = agent.select_action(state, evaluate=True)
        state, _, done, _ = env_break.step(weights)
        
    # 5. Evaluate Buy & Hold
    env_bah.reset()
    # Use equal weight across stocks and zero for cash to represent pure buy & hold
    bah_weights = np.zeros(n_total_assets)
    bah_weights[:n_assets] = 1.0 / n_assets
    for t in range(len(returns) - 1):
        env_bah.step(bah_weights)
        
    # Results
    drl_metrics = calculate_performance_metrics(env_break.nav_history)
    bah_metrics = calculate_performance_metrics(env_bah.nav_history)
    
    print("\n" + "=" * 80)
    print(" 🏆 KẾT QUẢ ĐÁNH GIÁ THỰC TIỄN (REAL MARKET DATA)")
    print("=" * 80)
    print(f" {'Chiến lược':<20} | {'CAGR (%)':>12} | {'Sharpe Ratio':>15} | {'Max Drawdown (%)':>20}")
    print("-" * 80)
    print(f" {'DRL-Break (Kalman)':<20} | {drl_metrics['cagr']:>+11.2f}% | {drl_metrics['sharpe']:>15.4f} | {drl_metrics['max_dd']:>19.2f}%")
    print(f" {'Buy & Hold':<20} | {bah_metrics['cagr']:>+11.2f}% | {bah_metrics['sharpe']:>15.4f} | {bah_metrics['max_dd']:>19.2f}%")
    print("=" * 80)
    print(f" Tài sản: {list(returns.columns)}")
    print(f" Thời gian: {returns.index[0]} đến {returns.index[-1]} ({len(returns)} phiên)")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    run_practical_evaluation()
