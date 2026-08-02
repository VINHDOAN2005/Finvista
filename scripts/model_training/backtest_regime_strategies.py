# -*- coding: utf-8 -*-
"""
📈 FINVISTA: KAIROS REGIME-BASED BACKTESTER (V4.0)
=================================================
Multi-layer institutional trading simulator:
1. Context Layer: KAIROS v3 Regimes.
2. Signal Layer: Adaptive Trend (S2/S3) & Mean Reversion (S7).
3. Risk Layer: Dynamic Kelly Sizing & ATR Stops.
4. Metrics: CAGR, Sharpe, MDD, Profit Factor, Regime Attribution.
"""

import pandas as pd
import numpy as np
import os
import sys
import warnings
from datetime import datetime

# Suppress warnings
warnings.filterwarnings('ignore')

sys.path.append(os.getcwd())
from src.modules.regime_analysis.indicators.regime_detector import RegimeDetector
from src.core.database import engine

# Trading Parameters
INITIAL_CASH = 1_000_000_000.0  # 1 Billion VND
COMMISSION = 0.0015             # 0.15% Buy/Sell fee
SLIPPAGE = 0.001                # 0.1% expected slippage
MAX_POSITIONS = 5
MAX_NAV_PER_STOCK = 0.20        # 20% max per ticker

class KairosBacktester:
    def __init__(self, symbols: list, start_date: str = "2023-01-01"):
        self.symbols = symbols
        self.start_date = start_date
        self.cash = INITIAL_CASH
        self.portfolio = {} # symbol -> {qty, buy_price, buy_date, entry_score}
        self.history = []   # List of closed trades
        self.equity_curve = []
        self.daily_metrics = []

    def calculate_indicators(self, df):
        """Prepare Layer 2 indicators."""
        df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
        df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
        df['vol_ma20'] = df['volume'].rolling(window=20).mean()
        
        # RSI 14
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi14'] = 100 - (100 / (1 + rs))
        
        # ATR 14 for stops
        tr = pd.concat([df['high'] - df['low'], (df['high'] - df['close'].shift()).abs(), (df['low'] - df['close'].shift()).abs()], axis=1).max(axis=1)
        df['atr14'] = tr.rolling(window=14).mean()
        
        return df

    def calculate_signal_score(self, row):
        """Layer 2.5: Signal Quality Score (0-100)."""
        # Regime Score (40%)
        regime = row['regime']
        regime_map = {
            "S3: Xu_Hướng_Mạnh": 100,
            "S2: Đầu_Xu_Hướng": 85,
            "S7: Quét_Thanh_Khoản": 80,
            "S4: Cao_Trào": 50,
            "S5: Hồi_Quy": 40,
            "S1: Nén_Chặt": 20,
            "S6: Nhiễu_Động": 0,
            "S0: Đóng_Băng": 0
        }
        r_score = regime_map.get(regime, 0)
        
        # Trend Score (30%)
        t_score = 100 if (row['ema20'] > row['ema50'] and row['close'] > row['ema20']) else 0
        
        # Volume Score (20%)
        v_ratio = row['volume'] / row['vol_ma20'] if row['vol_ma20'] > 0 else 1
        v_score = min(100, v_ratio * 50)
        
        # Volatility Score (10% - Inverse of vol to favor stability)
        vol_score = max(0, 100 - (row['vol_30'] * 100))
        
        total_score = (r_score * 0.4) + (t_score * 0.3) + (v_score * 0.2) + (vol_score * 0.1)
        return total_score

    def run(self):
        print(f"🚀 Initializing Backtest for {len(self.symbols)} tickers...")
        
        # 1. Prepare Data
        data_bundle = {}
        for symbol in self.symbols:
            query = f"SELECT * FROM stock_history WHERE symbol='{symbol}' ORDER BY date ASC"
            df = pd.read_sql(query, engine)
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            df = self.calculate_indicators(df)
            
            # Layer 1: Kairos v3 Regimes
            regime_df = RegimeDetector.calculate_kairos_regimes(df)
            df['regime'] = regime_df['regime']
            df['vol_30'] = regime_df['vol_30']
            
            # Layer 2.5: Signal Score
            df['signal_score'] = df.apply(self.calculate_signal_score, axis=1)
            
            data_bundle[symbol] = df

        # 2. Global Timeline Simulation
        all_dates = sorted(pd.concat([df.index.to_series() for df in data_bundle.values()]).unique())
        all_dates = [d for d in all_dates if d >= pd.to_datetime(self.start_date)]
        
        for current_date in all_dates:
            # 2.1 Update Portfolio Value & Equity Curve
            pos_val = 0
            for sym, pos in self.portfolio.items():
                curr_price = data_bundle[sym].loc[current_date, 'close'] if current_date in data_bundle[sym].index else pos['buy_price']
                pos_val += pos['qty'] * curr_price
            
            total_nav = self.cash + pos_val
            self.equity_curve.append({'date': current_date, 'nav': total_nav})

            # 2.2 Manage Existing Positions (Exits)
            to_sell = []
            for sym, pos in self.portfolio.items():
                if current_date not in data_bundle[sym].index: continue
                row = data_bundle[sym].loc[current_date]
                
                # Exit Logic:
                # - S4 (Climax) or S6 (Turbulence) exit
                # - Stop Loss: 2 * ATR
                # - Trailing Stop: Close < EMA20
                price = row['close']
                days_held = (current_date - pd.to_datetime(pos['buy_date'])).days
                
                # Stop Loss Check
                stop_price = pos['buy_price'] - (2 * pos['atr_at_buy'])
                
                reason = None
                if price < stop_price: reason = "STOP_LOSS"
                elif row['regime'] in ["S4: Cao_Trào", "S6: Nhiễu_Động"]: reason = "REGIME_EXIT"
                elif days_held > 5 and price < row['ema20'] * 0.98: reason = "TREND_BREAK"
                
                if reason:
                    to_sell.append((sym, price, reason))

            for sym, price, reason in to_sell:
                pos = self.portfolio.pop(sym)
                gross = pos['qty'] * price
                fee = gross * (COMMISSION + SLIPPAGE)
                net = gross - fee
                self.cash += net
                
                # Record trade
                p_l = net - pos['total_cost']
                p_l_pct = (p_l / pos['total_cost']) * 100
                self.history.append({
                    'symbol': sym,
                    'buy_date': pos['buy_date'],
                    'sell_date': current_date,
                    'buy_price': pos['buy_price'],
                    'sell_price': price,
                    'p_l_vnd': p_l,
                    'p_l_pct': p_l_pct,
                    'regime_at_buy': pos['regime_at_buy'],
                    'reason': reason
                })

            # 2.3 Find Entry Candidates
            if len(self.portfolio) >= MAX_POSITIONS: continue
            
            candidates = []
            for sym in self.symbols:
                if sym in self.portfolio or current_date not in data_bundle[sym].index: continue
                row = data_bundle[sym].loc[current_date]
                
                # STRATEGY A: TREND (S2/S3 + EMA + VOL)
                is_trend = (row['regime'] in ["S2: Đầu_Xu_Hướng", "S3: Xu_Hướng_Mạnh"] and 
                            row['ema20'] > row['ema50'] and 
                            row['close'] > row['ema20'] and 
                            row['volume'] > row['vol_ma20'])
                
                # STRATEGY B: REVERSAL (S7 + RSI + CONFIRMATION)
                is_reversal = (row['regime'] == "S7: Quét_Thanh_Khoản" and 
                               row['rsi14'] < 30 and 
                               row['close'] > row['open']) # Bullish candle confirmation
                
                if (is_trend or is_reversal) and row['signal_score'] >= 65:
                    candidates.append({
                        'symbol': sym,
                        'price': row['close'],
                        'score': row['signal_score'],
                        'regime': row['regime'],
                        'atr': row['atr14']
                    })
            
            # Sort by Signal Quality Score
            candidates = sorted(candidates, key=lambda x: x['score'], reverse=True)
            
            for cand in candidates:
                if len(self.portfolio) >= MAX_POSITIONS: break
                
                # Sizing: Kelly-Lite (Allocation based on score)
                # Max 20% NAV per stock
                alloc_ratio = (cand['score'] / 100) * MAX_NAV_PER_STOCK
                target_val = total_nav * alloc_ratio
                
                if self.cash < target_val: target_val = self.cash
                
                fee = target_val * (COMMISSION + SLIPPAGE)
                net_val = target_val - fee
                
                if net_val <= 0: continue
                
                qty = int(net_val / cand['price'])
                if qty <= 0: continue
                
                self.cash -= target_val
                self.portfolio[cand['symbol']] = {
                    'qty': qty,
                    'buy_price': cand['price'],
                    'buy_date': current_date,
                    'total_cost': target_val,
                    'regime_at_buy': cand['regime'],
                    'atr_at_buy': cand['atr'],
                    'entry_score': cand['score']
                }

    def report(self):
        equity_df = pd.DataFrame(self.equity_curve).set_index('date')
        if equity_df.empty:
            print("❌ No trades executed in the backtest.")
            return

        # 1. Key Metrics
        returns = equity_df['nav'].pct_change().dropna()
        total_ret = (equity_df['nav'].iloc[-1] / INITIAL_CASH - 1) * 100
        days = (equity_df.index[-1] - equity_df.index[0]).days
        cagr = ((equity_df['nav'].iloc[-1] / INITIAL_CASH) ** (365.0 / days) - 1) * 100
        sharpe = (returns.mean() / returns.std()) * np.sqrt(252) if returns.std() > 0 else 0
        
        mdd_df = equity_df['nav'] / equity_df['nav'].cummax() - 1
        mdd = mdd_df.min() * 100
        
        calmar = cagr / abs(mdd) if mdd != 0 else 0
        
        trades_df = pd.DataFrame(self.history)
        win_rate = (trades_df['p_l_vnd'] > 0).mean() * 100 if not trades_df.empty else 0
        profit_factor = trades_df[trades_df['p_l_vnd'] > 0]['p_l_vnd'].sum() / abs(trades_df[trades_df['p_l_vnd'] < 0]['p_l_vnd'].sum()) if not trades_df.empty and trades_df[trades_df['p_l_vnd'] < 0]['p_l_vnd'].sum() != 0 else 0
        
        print("\n" + "="*60)
        print(" 🏆 FINVISTA STRATEGY PERFORMANCE REPORT ".center(60))
        print("="*60)
        print(f" Total Return:    {total_ret:>12.2f}%")
        print(f" CAGR:            {cagr:>12.2f}%")
        print(f" Sharpe Ratio:    {sharpe:>12.2f}")
        print(f" Max Drawdown:    {mdd:>12.2f}%")
        print(f" Calmar Ratio:    {calmar:>12.2f}")
        print(f" Win Rate:        {win_rate:>12.2f}%")
        print(f" Profit Factor:   {profit_factor:>12.2f}")
        print(f" Total Trades:    {len(trades_df):>12}")
        print("-" * 60)

        # 2. Regime Attribution Report
        print("\n 🧩 REGIME ATTRIBUTION REPORT (Where is the Alpha?)")
        if not trades_df.empty:
            attr = trades_df.groupby('regime_at_buy').agg({
                'p_l_vnd': ['sum', 'count', 'mean'],
                'p_l_pct': 'mean'
            })
            attr.columns = ['Total_P/L_VND', 'Trade_Count', 'Avg_P/L_VND', 'Avg_P/L_%']
            print(attr.sort_values(by='Total_P/L_VND', ascending=False).to_string())
        
        print("="*60 + "\n")
        
        # Save equity curve for visual inspection if needed
        equity_df.to_csv("data/processed/backtest_equity_curve.csv")

if __name__ == "__main__":
    # Institutional Basket
    symbols = ["FPT", "VHM", "HPG", "VIC", "MSN", "MWG", "TCB", "VCB", "STB", "SSI"]
    bt = KairosBacktester(symbols, start_date="2022-01-01")
    bt.run()
    bt.report()
