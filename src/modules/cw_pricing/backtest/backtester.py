# -*- coding: utf-8 -*-
"""
🏆 FINVISTA: QUANTITATIVE BACKTESTER
====================================
Simulates trading strategies using historical data from the SQLite database.
Combines Covered Warrant (CW) price action with Underlying Stock (CPCS) data.

Strategies supported:
- Delta-Neutral Hedging (Volatility Arbitrage)
- Directional Breakout (Technical)
- Theta Decay Stop-loss

Author: Antigravity
"""
import pandas as pd
import numpy as np
from datetime import datetime
from scipy.stats import norm
from src.core.database import engine
from src.modules.cw_pricing.models.pricing_core import calculate_greeks_for_cw, RISK_FREE_RATE
import sys

# Force stdout encoding to UTF-8 to handle emojis on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

class FinvistaBacktester:
    def __init__(self):
        self.engine = engine

    def load_historical_data(self, symbol: str, underlying: str):
        """Load and merge historical OHLCV data for CW and Stock from the DB."""
        query = f"""
            SELECT 
                c.date,
                c.open as cw_open,
                c.high as cw_high,
                c.low as cw_low,
                c.close as cw_close,
                c.volume as cw_volume,
                s.open as stock_open,
                s.high as stock_high,
                s.low as stock_low,
                s.close as stock_close
            FROM cw_history c
            JOIN stock_history s ON c.date = s.date AND s.symbol = '{underlying}'
            WHERE c.symbol = '{symbol}'
            ORDER BY c.date ASC
        """
        df = pd.read_sql(query, self.engine)
        if df.empty:
            raise ValueError(f"No historical data found for {symbol} and {underlying}.")
        return df

    def inject_historical_derivatives_sentiment(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Fetches historical VN30 and VN30F1M data corresponding to the backtest date range,
        calculates Basis Z-Score, and merges it back into the backtest DataFrame.
        """
        try:
            import vnstock
            from datetime import timedelta
        except ImportError:
            print("⚠️ vnstock not found. Defaulting to NEUTRAL market sentiment.")
            df['market_sentiment'] = 'NEUTRAL'
            df['basis_zscore'] = 0.0
            return df
            
        if df.empty:
            return df
            
        dates = pd.to_datetime(df['date']).sort_values()
        min_date = dates.iloc[0]
        max_date = dates.iloc[-1]
        
        # Take 45 extra days of historical buffer to calculate rolling mean & std for the first days
        start_date = (min_date - timedelta(days=45)).strftime('%Y-%m-%d')
        end_date = max_date.strftime('%Y-%m-%d')
        
        try:
            print(f"📡 Downloading historical VN30 and VN30F1M from {start_date} to {end_date} for derivatives sentiment filter...")
            f1m_quote = vnstock.Quote(symbol='VN30F1M')
            df_f1m = f1m_quote.history(start=start_date, end=end_date)
            
            vn30_quote = vnstock.Quote(symbol='VN30')
            df_vn30 = vn30_quote.history(start=start_date, end=end_date)
            
            if df_f1m.empty or df_vn30.empty:
                print("⚠️ Historical derivatives data not fetched. Defaulting to NEUTRAL sentiment.")
                df['market_sentiment'] = 'NEUTRAL'
                df['basis_zscore'] = 0.0
                return df
                
            for d in [df_f1m, df_vn30]:
                if 'time' in d.columns:
                    d.rename(columns={'time': 'date'}, inplace=True)
                d['date'] = pd.to_datetime(d['date'])
                
            merged = pd.merge(
                df_f1m[['date', 'close']], 
                df_vn30[['date', 'close']], 
                on='date', 
                suffixes=('_f1m', '_vn30')
            ).sort_values('date').reset_index(drop=True)
            
            merged['basis'] = merged['close_f1m'] - merged['close_vn30']
            
            # Rolling Z-score over 20 sessions
            window = min(20, len(merged))
            rolling_mean = merged['basis'].rolling(window).mean()
            rolling_std = merged['basis'].rolling(window).std().fillna(1.5).replace(0.0, 1.5)
            merged['basis_zscore'] = (merged['basis'] - rolling_mean) / rolling_std
            
            def get_sentiment(row):
                z = row['basis_zscore']
                b = row['basis']
                if pd.isna(z):
                    return 'NEUTRAL'
                if z <= -1.5 or b < -6.0:
                    return 'BEARISH'
                elif z >= 1.5 or b > 3.0:
                    return 'BULLISH'
                return 'NEUTRAL'
                
            merged['market_sentiment'] = merged.apply(get_sentiment, axis=1)
            
            # Merge back to original dataframe on date
            df['date_dt'] = pd.to_datetime(df['date'])
            df = pd.merge(
                df, 
                merged[['date', 'market_sentiment', 'basis_zscore']], 
                left_on='date_dt', 
                right_on='date', 
                how='left',
                suffixes=('', '_deriv')
            )
            df.drop(columns=['date_dt', 'date_deriv'], errors='ignore', inplace=True)
            df['market_sentiment'] = df['market_sentiment'].fillna('NEUTRAL')
            df['basis_zscore'] = df['basis_zscore'].fillna(0.0)
            
        except Exception as e:
            print(f"⚠️ Error calculating historical derivatives sentiment: {e}. Defaulting to NEUTRAL.")
            df['market_sentiment'] = 'NEUTRAL'
            df['basis_zscore'] = 0.0
            
        return df

    def run_volatility_arbitrage(self, symbol: str, underlying: str, strike: float, ratio: float, expiry_date: str, risk_free_rate: float = RISK_FREE_RATE, use_derivatives_filter: bool = False):
        """
        Simulate a simple volatility arbitrage strategy.
        Buy CW when its Implied Volatility is low relative to recent Historical Volatility.
        """
        df = self.load_historical_data(symbol, underlying)
        if use_derivatives_filter:
            df = self.inject_historical_derivatives_sentiment(df)
        
        # Calculate Rolling Historical Volatility (30 days) of the underlying stock
        df['log_ret'] = np.log(df['stock_close'] / df['stock_close'].shift(1))
        df['rolling_hv_30'] = df['log_ret'].rolling(window=30).std() * np.sqrt(240)
        
        # We need actual time to maturity for each day to calculate IV
        expiry = datetime.strptime(expiry_date, "%Y-%m-%d")
        
        results = []
        for index, row in df.iterrows():
            current_date = datetime.strptime(row['date'], "%Y-%m-%d")
            days_to_expiry = (expiry - current_date).days
            
            if days_to_expiry <= 0 or pd.isna(row['rolling_hv_30']):
                continue
            
            # Using our pricing core to calculate theoretical values and Greeks
            # We pass the rolling HV to see the theoretical price
            greeks = calculate_greeks_for_cw(
                underlying_price=row['stock_close'],
                strike_price=strike,
                days_to_maturity=days_to_expiry,
                implied_volatility=row['rolling_hv_30'],
                conversion_ratio=ratio,
                risk_free_rate=risk_free_rate
            )
            
            # We need to calculate theoretical price using the black scholes formula directly since calculate_greeks_for_cw doesn't return theo_price
            T_years = days_to_expiry / 365.0
            from src.modules.cw_pricing.models.pricing_core import calculate_d1_d2
            d1, d2 = calculate_d1_d2(row['stock_close'], strike, T_years, risk_free_rate, row['rolling_hv_30'])
            theo_price = (row['stock_close'] * norm.cdf(d1) - strike * np.exp(-risk_free_rate * T_years) * norm.cdf(d2)) / ratio
            
            # If actual price < theoretical price, it's underpriced (IV < HV).
            is_underpriced = row['cw_close'] < theo_price
            
            signal = 'BUY' if is_underpriced else 'WAIT'
            if use_derivatives_filter and row.get('market_sentiment', 'NEUTRAL') == 'BEARISH':
                signal = 'WAIT'
            
            results.append({
                'date': row['date'],
                'cw_close': row['cw_close'],
                'stock_close': row['stock_close'],
                'days_to_expiry': days_to_expiry,
                'rolling_hv': row['rolling_hv_30'],
                'theo_price': theo_price,
                'delta': greeks['delta'],
                'signal': signal
            })
            
        return pd.DataFrame(results)

    def run_pro_quant_strategy(self, symbol: str, underlying: str, use_derivatives_filter: bool = False):
        """
        Chiến lược Thực chiến chuyên sâu (Pro Quant Strategy):
        Kết hợp Nghiên cứu định lượng (Greeks) + Động lượng (TA) + Quản trị rủi ro (SL/TP).
        """
        import pandas_ta as ta
        import warnings
        warnings.filterwarnings('ignore')
        
        df = self.load_historical_data(symbol, underlying)
        if use_derivatives_filter:
            df = self.inject_historical_derivatives_sentiment(df)
        
        # 1. Tính toán Đặc trưng Cổ phiếu (Underlying Features)
        df['stock_open'] = df['stock_open'].astype(float)
        df['stock_high'] = df['stock_high'].astype(float)
        df['stock_low'] = df['stock_low'].astype(float)
        df['stock_close'] = df['stock_close'].astype(float)
        
        # Thêm các chỉ báo theo trend (Ngắn hạn để phù hợp dữ liệu ngắn của CW)
        df.ta.ema(close='stock_close', length=10, append=True)
        df.ta.ema(close='stock_close', length=20, append=True)
        df.ta.rsi(close='stock_close', length=14, append=True)
        df.ta.atr(high='stock_high', low='stock_low', close='stock_close', length=14, append=True)
        df['stock_volume_sma_20'] = df['cw_volume'].rolling(20).mean() # Approximate liquidity
        
        df.dropna(inplace=True)
        
        ema10_col = [c for c in df.columns if c.startswith('EMA_10')][0]
        ema20_col = [c for c in df.columns if c.startswith('EMA_20')][0]
        rsi_col = [c for c in df.columns if c.startswith('RSI_')][0]
        atr_col = [c for c in df.columns if c.startswith('ATRr_')][0]
        
        results = []
        
        # State Machine for Trade Management
        in_position = False
        entry_cw_price = 0.0
        entry_stock_price = 0.0
        stop_loss_stock = 0.0
        days_held = 0 # Track T+2.5 mechanism
        consecutive_bearish = 0
        
        for index, row in df.iterrows():
            sentiment = row.get('market_sentiment', 'NEUTRAL')
            if sentiment == 'BEARISH':
                consecutive_bearish += 1
            else:
                consecutive_bearish = 0
                
            signal = 'WAIT'
            current_cw_price = row['cw_close']
            current_stock_price = row['stock_close']
            
            # Quản trị vị thế đang mở
            if in_position:
                days_held += 1
                can_sell = days_held >= 2
                
                # FINVISTA INSTITUTIONAL UPGRADE: "Theta Bomb" Avoidance
                # Force sell if held for too long (approaching expiry) to avoid rapid time value decay
                is_theta_bomb = False
                if days_held > 40: # Heuristic: if we hold a short-term CW for 40 trading days, it's likely getting too close to maturity
                    is_theta_bomb = True

                # Check early exit if derivatives sentiment goes bearish for 2 consecutive days
                if use_derivatives_filter and consecutive_bearish >= 2 and can_sell:
                    signal = 'SELL'
                    in_position = False
                    days_held = 0
                # "Theta Bomb" Exit Check
                elif is_theta_bomb and can_sell:
                    signal = 'SELL'
                    in_position = False
                    days_held = 0
                # 1. Check Stop Loss (Cắt lỗ động theo ATR trên Cổ phiếu cơ sở)
                elif current_stock_price <= stop_loss_stock and can_sell:
                    signal = 'SELL'
                    in_position = False
                    days_held = 0
                # 2. Check Trend-break Exit (CPCS gãy xu hướng EMA20 - cắt lỗ/chốt lời sớm)
                elif current_stock_price < row[ema20_col] and can_sell:
                    signal = 'SELL'
                    in_position = False
                    days_held = 0
                # 3. Trailing Stop (Chỉ cập nhật tịnh tiến khi cổ phiếu cơ sở vượt +5% từ điểm mua)
                else:
                    if current_stock_price >= entry_stock_price * 1.05:
                        new_sl = current_stock_price - (row[atr_col] * 1.5)
                        if new_sl > stop_loss_stock:
                            stop_loss_stock = new_sl
                    signal = 'HOLD'
            
            # Tìm kiếm cơ hội vào lệnh (Entry Logic)
            if not in_position:
                is_uptrend = row[ema10_col] > row[ema20_col]
                is_pullback = current_stock_price <= (row[ema10_col] * 1.02) and current_stock_price >= (row[ema10_col] * 0.98)
                is_rsi_cool = row[rsi_col] < 60
                is_liquid = row['cw_volume'] > 5000 
                
                # Filter out entry if derivatives sentiment is bearish
                is_sentiment_ok = True
                if use_derivatives_filter and row.get('market_sentiment', 'NEUTRAL') == 'BEARISH':
                    is_sentiment_ok = False
                
                if is_uptrend and is_pullback and is_rsi_cool and is_liquid and current_cw_price > 100 and is_sentiment_ok:
                    signal = 'BUY'
                    in_position = True
                    entry_cw_price = current_cw_price
                    entry_stock_price = current_stock_price
                    # Cắt lỗ động theo ATR (2 lần ATR dưới giá mua)
                    stop_loss_stock = entry_stock_price - (row[atr_col] * 2.0)
            
            results.append({
                'date': row['date'],
                'cw_close': row['cw_close'],
                'stock_close': row['stock_close'],
                'signal': signal
            })
            
        return pd.DataFrame(results)

    def run_ultimate_panic_buy_strategy(self, symbol: str, underlying: str, use_derivatives_filter: bool = False):
        """
        🏆 CHIẾN LƯỢC CHÉN THÁNH V5 (Ultimate Panic Buy Strategy):
        Chỉ giao dịch nếu Chứng quyền vượt qua bộ lọc cấu trúc TIER 2 (Sweet Spot):
        - Moneyness: ITM, DEEP ITM, hoặc ATM
        - Delta: >= 0.25
        Tín hiệu vào lệnh: RSI < 40 + Nổ Volume Stock + Bollinger Band Width > 5% + Thị giá > 300đ.
        """
        import os
        import pandas_ta as ta
        import warnings
        warnings.filterwarnings('ignore')
        
        # 1. Kiểm tra điều kiện lọc cấu trúc (Structural Pre-filter)
        report_path = os.path.join("data", "processed", "excel_cw_report.csv")
        is_eligible = True
        reason = ""
        
        if os.path.exists(report_path):
            try:
                struct_df = pd.read_csv(report_path, encoding='utf-8')
                cw_info = struct_df[struct_df['A_MaCW'] == symbol]
                if not cw_info.empty:
                    moneyness = cw_info.iloc[0]['K_ITM_OTM']
                    delta = abs(float(cw_info.iloc[0]['T_Delta']))
                    
                    if moneyness not in ['ITM', 'DEEP ITM', 'ATM']:
                        is_eligible = False
                        reason = f"Trạng thái {moneyness} (Yêu cầu: ITM/ATM)"
                    elif delta < 0.25:
                        is_eligible = False
                        reason = f"Delta = {delta:.2f} < 0.25"
                else:
                    print(f"⚠️  Không tìm thấy thông tin cấu trúc cho {symbol} trong excel_cw_report.csv. Vẫn tiếp tục giao dịch ở chế độ rủi ro.")
            except Exception as e:
                print(f"⚠️  Lỗi đọc file cấu trúc: {e}")
                
        if not is_eligible:
            print(f"🛑 BỎ QUA GIAO DỊCH {symbol}: Không đạt chuẩn Tier 2 ({reason}) để bảo vệ vốn.")
            # Trả về DataFrame rỗng hoặc chỉ có tín hiệu WAIT để không giao dịch
            df = self.load_historical_data(symbol, underlying)
            df['signal'] = 'WAIT'
            return df[['date', 'cw_close', 'stock_close', 'signal']]
            
        # 2. Tính toán kỹ thuật
        df = self.load_historical_data(symbol, underlying)
        if use_derivatives_filter:
            df = self.inject_historical_derivatives_sentiment(df)
            
        df['stock_open'] = df['stock_open'].astype(float)
        df['stock_high'] = df['stock_high'].astype(float)
        df['stock_low'] = df['stock_low'].astype(float)
        df['stock_close'] = df['stock_close'].astype(float)
        df['stock_volume'] = df['stock_volume'].astype(float) if 'stock_volume' in df.columns else 0.0
        
        # Lấy dữ liệu Stock Volume trực tiếp từ DB nếu chưa có
        if 'stock_volume' not in df.columns or (df['stock_volume'] == 0).all():
            vol_query = f"SELECT date, volume as stock_volume FROM stock_history WHERE symbol = '{underlying}'"
            vol_df = pd.read_sql(vol_query, self.engine)
            df = df.drop(columns=['stock_volume'], errors='ignore').merge(vol_df, on='date', how='left')
            
        # Tính RSI, SMA20, Bollinger Bands
        df.ta.rsi(close='stock_close', length=14, append=True)
        df.ta.ema(close='stock_close', length=15, append=True)
        df['SMA20'] = df['stock_close'].rolling(20).mean()
        rolling_std = df['stock_close'].rolling(20).std()
        df['BBU_20'] = df['SMA20'] + (2 * rolling_std)
        df['BBL_20'] = df['SMA20'] - (2 * rolling_std)
        df['BBB_20'] = (df['BBU_20'] - df['BBL_20']) / df['SMA20'] * 100
        df['stock_volume_sma20'] = df['stock_volume'].rolling(20).mean()
        
        df.dropna(inplace=True)
        rsi_col = [c for c in df.columns if c.startswith('RSI_')][0]
        ema15_col = [c for c in df.columns if c.startswith('EMA_15')][0]
        
        results = []
        in_position = False
        entry_price = 0.0
        days_held = 0
        consecutive_bearish = 0
        
        for index, row in df.iterrows():
            sentiment = row.get('market_sentiment', 'NEUTRAL')
            if sentiment == 'BEARISH':
                consecutive_bearish += 1
            else:
                consecutive_bearish = 0
                
            signal = 'WAIT'
            current_cw_price = row['cw_close']
            current_stock_price = row['stock_close']
            
            if in_position:
                days_held += 1
                can_sell = days_held >= 2
                
                # Check early exit if derivatives sentiment goes bearish for 2 consecutive days
                if use_derivatives_filter and consecutive_bearish >= 2 and can_sell:
                    signal = 'SELL'
                    in_position = False
                    days_held = 0
                # 1. Check Stop Loss (Cắt lỗ cứng -15% hoặc Trailing Stop tịnh tiến)
                elif current_cw_price <= stop_loss and can_sell:
                    signal = 'SELL'
                    in_position = False
                    days_held = 0
                # 2. Check Trend-break Exit (CPCS gãy xu hướng EMA15 - cắt lỗ/chốt lời sớm)
                elif current_stock_price < row[ema15_col] and can_sell:
                    signal = 'SELL'
                    in_position = False
                    days_held = 0
                # 3. Trailing Stop (Chỉ cập nhật tịnh tiến khi giá đã vượt +8% từ điểm mua)
                else:
                    if current_cw_price >= entry_price * 1.08:
                        new_sl = current_cw_price * 0.93
                        if new_sl > stop_loss:
                            stop_loss = new_sl
                    signal = 'HOLD'
            else:
                is_washout = row['stock_volume'] > (row['stock_volume_sma20'] * 1.2)
                is_capitulation = row['BBB_20'] > 5
                
                # Filter out entry if derivatives sentiment is bearish
                is_sentiment_ok = True
                if use_derivatives_filter and row.get('market_sentiment', 'NEUTRAL') == 'BEARISH':
                    is_sentiment_ok = False
                
                # FINVISTA INSTITUTIONAL UPGRADE: Orderbook Imbalance (Level 2)
                is_orderbook_safe = True
                try:
                    from src.infra.orderbook_scraper import analyze_imbalance
                    ob_analysis = analyze_imbalance(symbol)
                    is_orderbook_safe = ob_analysis.get('is_safe_to_buy', True)
                except Exception as e:
                    pass
                
                if row[rsi_col] < 40 and is_washout and is_capitulation and current_cw_price > 300 and is_sentiment_ok and is_orderbook_safe:
                    signal = 'BUY'
                    in_position = True
                    entry_price = current_cw_price
                    days_held = 0
                    stop_loss = entry_price * 0.85
                    
            results.append({
                'date': row['date'],
                'cw_close': row['cw_close'],
                'stock_close': row['stock_close'],
                'signal': signal
            })
            
        return pd.DataFrame(results)

    def evaluate_performance(self, df: pd.DataFrame, initial_capital: float = 100000000.0, allocation_pct: float = 0.50) -> dict:
        """
        Simulate portfolio P/L based on backtest signals to calculate Quantitative KPIs:
        Sharpe Ratio, Maximum Drawdown, Win Rate, Kelly Criterion, and Total Return.
        """
        if df.empty or 'signal' not in df.columns:
            return {}

        cash = initial_capital
        position = 0
        buy_price = 0
        trades = []
        equity_curve = []

        for index, row in df.iterrows():
            current_price = row['cw_close']
            signal = row['signal']
            
            # Simple simulation logic
            if signal == 'BUY' and position == 0:
                # Dynamic Position Sizing: Use Kelly Criterion if we have enough trade history, else fixed allocation
                if len(trades) > 5:
                    win_prob = len([t for t in trades if t > 0]) / len(trades)
                    avg_win = np.mean([t for t in trades if t > 0]) if any(t > 0 for t in trades) else 0.01
                    avg_loss = abs(np.mean([t for t in trades if t < 0])) if any(t < 0 for t in trades) else 0.01
                    
                    if avg_loss > 0 and avg_win > 0:
                        win_loss_ratio = avg_win / avg_loss
                        kelly_fraction = win_prob - ((1 - win_prob) / win_loss_ratio)
                        # Cap Kelly fraction between 10% and 90%
                        dynamic_allocation = max(0.10, min(0.90, kelly_fraction * 0.5)) # Half-Kelly for safety
                    else:
                        dynamic_allocation = allocation_pct
                else:
                    dynamic_allocation = allocation_pct

                # Calculate how many lots we can buy based on dynamic allocation
                qty = (cash * dynamic_allocation) // (current_price * 100) * 100
                if qty > 0:
                    position = qty
                    buy_price = current_price
                    cash -= position * buy_price
                    
            elif signal == 'SELL' and position > 0:
                # Sell
                revenue = position * current_price
                cash += revenue
                p_l = (current_price - buy_price) / buy_price
                trades.append(p_l)
                position = 0
                buy_price = 0
            
            # If signal == 'WAIT' and we are holding from a basic strategy without SELL, auto-sell it:
            elif signal == 'WAIT' and position > 0:
                revenue = position * current_price
                cash += revenue
                p_l = (current_price - buy_price) / buy_price
                trades.append(p_l)
                position = 0
                buy_price = 0
                
            # If signal == 'HOLD', do nothing (just hold the position)

            # Record daily equity
            current_equity = cash + (position * current_price)
            equity_curve.append(current_equity)

        # Force close any open positions at the end to evaluate final P/L
        if position > 0:
            p_l = (current_price - buy_price) / buy_price
            trades.append(p_l)

        # Calculate Metrics
        total_return_pct = ((current_equity - initial_capital) / initial_capital) * 100
        win_rate = (len([t for t in trades if t > 0]) / len(trades) * 100) if trades else 0.0
        avg_trade_return = (sum(trades) / len(trades) * 100) if trades else 0.0
        
        # Calculate Max Drawdown
        equity_series = pd.Series(equity_curve)
        rolling_max = equity_series.cummax()
        drawdown = (equity_series - rolling_max) / rolling_max
        max_drawdown = drawdown.min() * 100
        
        # Calculate Sharpe Ratio (using dynamic Risk-Free Rate)
        daily_returns = equity_series.pct_change().dropna()
        if len(daily_returns) > 0 and daily_returns.std() != 0:
            # Assuming 252 trading days
            daily_rf = RISK_FREE_RATE / 252.0
            sharpe_ratio = ((daily_returns.mean() - daily_rf) / daily_returns.std()) * np.sqrt(252)
        else:
            sharpe_ratio = 0.0
            
        # Calculate global Kelly
        global_kelly = 0.0
        if trades:
            win_prob = len([t for t in trades if t > 0]) / len(trades)
            avg_win = np.mean([t for t in trades if t > 0]) if any(t > 0 for t in trades) else 0.0
            avg_loss = abs(np.mean([t for t in trades if t < 0])) if any(t < 0 for t in trades) else 0.0
            if avg_loss > 0 and avg_win > 0:
                global_kelly = (win_prob - ((1 - win_prob) / (avg_win / avg_loss))) * 100

        return {
            "Total Portfolio Return (%)": round(total_return_pct, 2),
            "Average Trade Return (%)": round(avg_trade_return, 2),
            "Total Trades": len(trades),
            "Win Rate (%)": round(win_rate, 2),
            "Max Drawdown (%)": round(max_drawdown, 2),
            "Sharpe Ratio": round(sharpe_ratio, 2),
            "Kelly (%)": round(global_kelly, 2),
            "Final Equity (VND)": current_equity
        }

if __name__ == "__main__":
    print("Initializing Backtester...")
    tester = FinvistaBacktester()
    try:
        # 1. Volatility Arbitrage
        res_quant_std = tester.run_volatility_arbitrage("CACB2510", "ACB", strike=22500.0, ratio=2.0, expiry_date="2026-06-23", use_derivatives_filter=False)
        metrics_quant_std = tester.evaluate_performance(res_quant_std)
        
        res_quant_filtered = tester.run_volatility_arbitrage("CACB2510", "ACB", strike=22500.0, ratio=2.0, expiry_date="2026-06-23", use_derivatives_filter=True)
        metrics_quant_filtered = tester.evaluate_performance(res_quant_filtered)
        
        # 2. Pro Quant
        res_ta_std = tester.run_pro_quant_strategy("CACB2510", "ACB", use_derivatives_filter=False)
        metrics_ta_std = tester.evaluate_performance(res_ta_std)
        
        res_ta_filtered = tester.run_pro_quant_strategy("CACB2510", "ACB", use_derivatives_filter=True)
        metrics_ta_filtered = tester.evaluate_performance(res_ta_filtered)
        
        # 3. Ultimate Panic Buy
        res_ultimate_std = tester.run_ultimate_panic_buy_strategy("CACB2510", "ACB", use_derivatives_filter=False)
        metrics_ultimate_std = tester.evaluate_performance(res_ultimate_std)
        
        res_ultimate_filtered = tester.run_ultimate_panic_buy_strategy("CACB2510", "ACB", use_derivatives_filter=True)
        metrics_ultimate_filtered = tester.evaluate_performance(res_ultimate_filtered)
        
        # Print comparison table
        print("\n" + "=" * 90)
        print(" 📊 BACKTEST COMPARISON: STANDARD vs. DERIVATIVES ADAPTIVE FILTER (CACB2510 / ACB)")
        print("=" * 90)
        print(f"{'Strategy & Mode':<37} | {'Return':<7} | {'Trades':<6} | {'WinRate':<7} | {'MaxDD':<7} | {'Sharpe':<6}")
        print("-" * 90)
        
        print(f"{'1. Volatility Arbitrage (Standard)':<37} | {metrics_quant_std.get('Total Portfolio Return (%)', 0):>6}% | {metrics_quant_std.get('Total Trades', 0):>6} | {metrics_quant_std.get('Win Rate (%)', 0):>6}% | {metrics_quant_std.get('Max Drawdown (%)', 0):>6}% | {metrics_quant_std.get('Sharpe Ratio', 0):>6}")
        print(f"{'   Volatility Arbitrage (Filtered)':<37} | {metrics_quant_filtered.get('Total Portfolio Return (%)', 0):>6}% | {metrics_quant_filtered.get('Total Trades', 0):>6} | {metrics_quant_filtered.get('Win Rate (%)', 0):>6}% | {metrics_quant_filtered.get('Max Drawdown (%)', 0):>6}% | {metrics_quant_filtered.get('Sharpe Ratio', 0):>6}")
        print("-" * 90)
        
        print(f"{'2. Pro Quant (Standard)':<37} | {metrics_ta_std.get('Total Portfolio Return (%)', 0):>6}% | {metrics_ta_std.get('Total Trades', 0):>6} | {metrics_ta_std.get('Win Rate (%)', 0):>6}% | {metrics_ta_std.get('Max Drawdown (%)', 0):>6}% | {metrics_ta_std.get('Sharpe Ratio', 0):>6}")
        print(f"{'   Pro Quant (Filtered)':<37} | {metrics_ta_filtered.get('Total Portfolio Return (%)', 0):>6}% | {metrics_ta_filtered.get('Total Trades', 0):>6} | {metrics_ta_filtered.get('Win Rate (%)', 0):>6}% | {metrics_ta_filtered.get('Max Drawdown (%)', 0):>6}% | {metrics_ta_filtered.get('Sharpe Ratio', 0):>6}")
        print("-" * 90)
        
        print(f"{'3. Ultimate Panic Buy (Standard)':<37} | {metrics_ultimate_std.get('Total Portfolio Return (%)', 0):>6}% | {metrics_ultimate_std.get('Total Trades', 0):>6} | {metrics_ultimate_std.get('Win Rate (%)', 0):>6}% | {metrics_ultimate_std.get('Max Drawdown (%)', 0):>6}% | {metrics_ultimate_std.get('Sharpe Ratio', 0):>6}")
        print(f"{'   Ultimate Panic Buy (Filtered)':<37} | {metrics_ultimate_filtered.get('Total Portfolio Return (%)', 0):>6}% | {metrics_ultimate_filtered.get('Total Trades', 0):>6} | {metrics_ultimate_filtered.get('Win Rate (%)', 0):>6}% | {metrics_ultimate_filtered.get('Max Drawdown (%)', 0):>6}% | {metrics_ultimate_filtered.get('Sharpe Ratio', 0):>6}")
        print("=" * 90)
        
    except Exception as e:
        print(f"Error during backtest: {e}")
