# -*- coding: utf-8 -*-
"""
📊 FINVISTA: PORTFOLIO OPTIMIZATION & ADVANCED TRADING STATISTICS
=================================================================
Quantitative portfolio analysis engine for Paper Trading accounts:
  1. Kelly Criterion Position Sizing (Full & Half-Kelly by underlying)
  2. Mean-Variance Optimization (Efficient Frontier allocation)
  3. Advanced Trading Statistics (deep-dive performance analytics)

Author: samvo
"""

import numpy as np
import pandas as pd
from datetime import datetime
from collections import defaultdict
import sys
if sys.platform == 'win32':
    import io
    if sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    if sys.stderr.encoding.lower() != 'utf-8':
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# ══════════════════════════════════════════════════════════════════════
# 1. DATA LOADING
# ══════════════════════════════════════════════════════════════════════

def load_trade_history(username: str = "demo") -> list:
    """Load completed round-trip trades (BUY → SELL pairs) from the portfolio history."""
    from src.modules.trading_engine.paper_trader import load_portfolio
    portfolio = load_portfolio(username=username)
    history = portfolio.get("history", [])
    
    # Build round-trip trades by matching BUY → SELL pairs
    buys = {}  # symbol -> list of buy records
    round_trips = []
    
    for tx in history:
        if tx["type"] == "BUY":
            sym = tx["symbol"]
            if sym not in buys:
                buys[sym] = []
            buys[sym].append(tx)
        elif tx["type"] == "SELL":
            sym = tx["symbol"]
            if sym in buys and buys[sym]:
                buy_tx = buys[sym].pop(0)
                
                buy_price = buy_tx["price"]
                sell_price = tx["price"]
                pnl_pct = (sell_price - buy_price) / buy_price * 100
                pnl_vnd = tx.get("p_l_vnd", (sell_price - buy_price) * tx["qty"])
                
                # Calculate holding period
                try:
                    buy_dt = datetime.fromisoformat(buy_tx["date"])
                    sell_dt = datetime.fromisoformat(tx["date"])
                    holding_days = max((sell_dt - buy_dt).days, 1)
                except Exception:
                    holding_days = 0
                
                round_trips.append({
                    "symbol": sym,
                    "underlying": tx.get("underlying", buy_tx.get("underlying", "N/A")),
                    "qty": tx["qty"],
                    "buy_price": buy_price,
                    "sell_price": sell_price,
                    "buy_date": buy_tx["date"],
                    "sell_date": tx["date"],
                    "buy_fee": buy_tx["fee"],
                    "sell_fee": tx["fee"],
                    "total_fee": buy_tx["fee"] + tx["fee"],
                    "pnl_pct": pnl_pct,
                    "pnl_vnd": pnl_vnd,
                    "win": pnl_vnd > 0,
                    "holding_days": holding_days,
                    "exit_reason": tx.get("reason", "UNKNOWN")
                })
    
    return round_trips, portfolio


_BACKTEST_TRADES_CACHE = None

def load_backtest_trades() -> list:
    """Load completed trades from the walk-forward backtest audit for analysis."""
    global _BACKTEST_TRADES_CACHE
    if _BACKTEST_TRADES_CACHE is not None:
        return _BACKTEST_TRADES_CACHE
        
    try:
        from src.modules.cw_pricing.backtest.opt_cw_backtest_audit import get_all_data, calc_indicators, run_strategy
        import pandas as pd
        
        print("  📡 Đang chuẩn bị dữ liệu backtest từ database...")
        df = get_all_data()
        if df.empty:
            print("  ⚠️ Không tìm thấy dữ liệu CW trong database.")
            return []
            
        df = calc_indicators(df)
        df['market_sentiment'] = 'NEUTRAL' # Skip fetching derivatives for speed in stats
        
        cw_groups = [g.sort_values('date').reset_index(drop=True) for _, g in df.groupby('cw_symbol') if len(g) >= 30]
        
        print(f"  🏁 Chạy chiến lược trên {len(cw_groups)} mã CW...")
        all_trades = run_strategy(
            cw_groups, 
            sl=0.80, 
            rsi_th=40,
            use_derivatives_filter=True, 
            use_adaptive_cb=True,
            trailing_act_pct=1.08,
            trailing_drop_pct=0.93,
            ema_col='EMA15',
            tp_pct=1.10,
            verbose=False
        )
        
        if not all_trades:
            return []
        
        round_trips = []
        for t in all_trades:
            pnl_pct = t.get("pnl_pct", 0.0)
            # Estimate VND P/L based on a 20M allocation per trade
            alloc = 20_000_000
            qty = alloc / t["entry_price"] if t["entry_price"] > 0 else 0
            pnl_vnd = qty * (t["exit_price"] - t["entry_price"])
            fee = alloc * 0.002  # ~0.2% round-trip fee estimate
            
            # Extract underlying from CW symbol (e.g. CACB2510 → ACB)
            cw_sym = t["cw"]
            underlying = cw_sym[1:4] if len(cw_sym) >= 5 else cw_sym
            # Fix common patterns: CACB -> ACB, CHPG -> HPG, CVPB -> VPB, etc.
            known_map = {
                "ACB": "ACB", "HPG": "HPG", "VPB": "VPB", "MBB": "MBB",
                "VIB": "VIB", "VHM": "VHM", "VRE": "VRE", "LPB": "LPB",
                "STB": "STB", "TCB": "TCB", "FPT": "FPT",
            }
            for prefix in known_map:
                if cw_sym[1:].startswith(prefix):
                    underlying = known_map[prefix]
                    break
            
            round_trips.append({
                "symbol": cw_sym,
                "underlying": underlying,
                "qty": int(qty),
                "buy_price": t["entry_price"],
                "sell_price": t["exit_price"],
                "buy_date": str(t["entry_date"]),
                "sell_date": str(t["exit_date"]),
                "buy_fee": fee / 2,
                "sell_fee": fee / 2,
                "total_fee": fee,
                "pnl_pct": pnl_pct,
                "pnl_vnd": pnl_vnd,
                "win": t.get("win", pnl_pct > 0),
                "holding_days": t.get("days_held", 0),
                "exit_reason": t.get("exit_type", "BACKTEST")
            })
        
        print(f"  ✅ Đã nạp {len(round_trips)} giao dịch từ backtest.")
        _BACKTEST_TRADES_CACHE = round_trips
        return round_trips
    except Exception as e:
        print(f"  ⚠️ Could not load backtest trades: {e}")
        import traceback; traceback.print_exc()
        return []


# ══════════════════════════════════════════════════════════════════════
# 2. KELLY CRITERION
# ══════════════════════════════════════════════════════════════════════

def calculate_kelly(trades: list) -> dict:
    """
    Calculate Kelly Criterion position sizing.
    
    Kelly% = W - (1 - W) / R
    where:
      W = Win Rate (probability of winning)
      R = Payoff Ratio (avg win / |avg loss|)
    """
    if not trades:
        return {"kelly_full": 0.0, "kelly_half": 0.0, "win_rate": 0.0, "payoff_ratio": 0.0}
    
    wins = [t for t in trades if t["win"]]
    losses = [t for t in trades if not t["win"]]
    
    win_rate = len(wins) / len(trades) if trades else 0.0
    
    avg_win = np.mean([t["pnl_pct"] for t in wins]) if wins else 0.0
    avg_loss = abs(np.mean([t["pnl_pct"] for t in losses])) if losses else 1.0
    
    payoff_ratio = avg_win / avg_loss if avg_loss > 0 else float("inf")
    
    if payoff_ratio == float("inf") or payoff_ratio == 0:
        kelly_full = win_rate * 100
    else:
        kelly_full = (win_rate - (1 - win_rate) / payoff_ratio) * 100
    
    kelly_half = kelly_full / 2.0  # Fractional Kelly (safer for real trading)
    
    return {
        "kelly_full": kelly_full,
        "kelly_half": kelly_half,
        "win_rate": win_rate * 100,
        "payoff_ratio": payoff_ratio,
        "avg_win": avg_win,
        "avg_loss": -abs(avg_loss),
        "total_trades": len(trades),
        "wins": len(wins),
        "losses": len(losses)
    }


def calculate_kelly_by_underlying(trades: list) -> list:
    """Calculate Kelly Criterion for each underlying stock group."""
    grouped = defaultdict(list)
    for t in trades:
        grouped[t["underlying"]].append(t)
    
    results = []
    for underlying, group_trades in sorted(grouped.items()):
        k = calculate_kelly(group_trades)
        results.append({
            "underlying": underlying,
            **k
        })
    
    return sorted(results, key=lambda x: x["kelly_half"], reverse=True)


# ══════════════════════════════════════════════════════════════════════
# 3. MEAN-VARIANCE OPTIMIZATION
# ══════════════════════════════════════════════════════════════════════

def mean_variance_optimize(trades: list) -> dict:
    """
    Simplified Mean-Variance Optimization using historical P/L returns 
    per underlying group to find the optimal capital allocation weights 
    that maximize the Sharpe Ratio.
    """
    grouped = defaultdict(list)
    for t in trades:
        grouped[t["underlying"]].append(t["pnl_pct"])
    
    underlyings = sorted(grouped.keys())
    n = len(underlyings)
    
    if n < 2:
        # With only 1 underlying, 100% allocation
        if n == 1:
            return {
                "weights": {underlyings[0]: 100.0},
                "expected_return": np.mean(grouped[underlyings[0]]),
                "portfolio_vol": np.std(grouped[underlyings[0]]),
                "sharpe": 0.0
            }
        return {"weights": {}, "expected_return": 0.0, "portfolio_vol": 0.0, "sharpe": 0.0}
    
    # Build return vectors (pad shorter ones with 0)
    max_len = max(len(v) for v in grouped.values())
    returns_matrix = np.zeros((max_len, n))
    for j, u in enumerate(underlyings):
        rets = grouped[u]
        returns_matrix[:len(rets), j] = rets
    
    # Mean returns and covariance
    mean_returns = np.mean(returns_matrix, axis=0)
    cov_matrix = np.cov(returns_matrix.T) if n > 1 else np.array([[np.var(returns_matrix)]])
    
    # Monte Carlo simulation to find optimal weights
    best_sharpe = -np.inf
    best_weights = np.ones(n) / n
    best_ret = 0.0
    best_vol = 0.0
    
    np.random.seed(42)
    for _ in range(50000):
        w = np.random.dirichlet(np.ones(n))
        port_ret = np.dot(w, mean_returns)
        port_vol = np.sqrt(np.dot(w.T, np.dot(cov_matrix, w)))
        
        if port_vol > 0:
            sharpe = port_ret / port_vol
        else:
            sharpe = 0.0
        
        if sharpe > best_sharpe:
            best_sharpe = sharpe
            best_weights = w
            best_ret = port_ret
            best_vol = port_vol
    
    weights_dict = {}
    for j, u in enumerate(underlyings):
        weights_dict[u] = round(best_weights[j] * 100, 1)
    
    return {
        "weights": weights_dict,
        "expected_return": best_ret,
        "portfolio_vol": best_vol,
        "sharpe": best_sharpe
    }


# ══════════════════════════════════════════════════════════════════════
# 4. EXIT REASON ANALYSIS
# ══════════════════════════════════════════════════════════════════════

def analyze_exit_reasons(trades: list) -> list:
    """Categorize trades by exit reason and compute statistics for each category."""
    categories = defaultdict(list)
    
    for t in trades:
        reason = t["exit_reason"]
        # Normalize reason categories
        if "TAKE PROFIT" in reason.upper() or "TP" in reason.upper():
            cat = "Take Profit (TP)"
        elif "STOP LOSS" in reason.upper() or "SL" in reason.upper():
            cat = "Stop Loss (SL)"
        elif "MATURITY" in reason.upper() or "EXPIRY" in reason.upper():
            cat = "Pre-Maturity Exit"
        elif "VOLATILITY" in reason.upper() or "CONVERGED" in reason.upper():
            cat = "Volatility Converged"
        else:
            cat = "Other"
        categories[cat].append(t)
    
    results = []
    for cat, cat_trades in sorted(categories.items()):
        wins = sum(1 for t in cat_trades if t["win"])
        avg_pnl = np.mean([t["pnl_pct"] for t in cat_trades])
        results.append({
            "category": cat,
            "count": len(cat_trades),
            "wins": wins,
            "losses": len(cat_trades) - wins,
            "win_rate": wins / len(cat_trades) * 100 if cat_trades else 0,
            "avg_pnl": avg_pnl,
            "total_pnl_vnd": sum(t["pnl_vnd"] for t in cat_trades)
        })
    
    return sorted(results, key=lambda x: x["count"], reverse=True)


# ══════════════════════════════════════════════════════════════════════
# 5. MAIN REPORT PRINTER
# ══════════════════════════════════════════════════════════════════════

def print_advanced_stats(username: str = "demo", use_backtest: bool = False):
    """Print a comprehensive portfolio optimization and trading statistics report."""
    source_label = "PAPER TRADING (Live)"
    
    if use_backtest:
        trades = load_backtest_trades()
        portfolio = {"initial_cash": 100_000_000, "cash": 100_000_000}
        source_label = "BACKTEST (Walk-Forward Audit)"
    else:
        trades, portfolio = load_trade_history(username=username)
        
        # Auto-fallback to backtest if no live trades
        if not trades:
            print("\n💡 Chưa có lệnh Paper Trading hoàn tất. Tự động chuyển sang dữ liệu Backtest...")
            trades = load_backtest_trades()
            portfolio = {"initial_cash": 100_000_000, "cash": 100_000_000}
            source_label = "BACKTEST (Walk-Forward Audit — Auto-Fallback)"
    
    if not trades:
        print("\n⚠️  Không tìm thấy dữ liệu giao dịch nào.")
        print("💡 Hãy chạy 'python run.py trade --scan' hoặc 'python run.py stats --backtest'.")
        return
    
    initial_cash = portfolio.get("initial_cash", 100_000_000)
    current_cash = portfolio.get("cash", initial_cash)
    
    # ── SECTION 1: OVERVIEW ──
    total = len(trades)
    wins = sum(1 for t in trades if t["win"])
    losses = total - wins
    win_rate = wins / total * 100
    
    total_pnl_vnd = sum(t["pnl_vnd"] for t in trades)
    total_fees = sum(t["total_fee"] for t in trades)
    
    winning_pnls = [t["pnl_pct"] for t in trades if t["win"]]
    losing_pnls = [t["pnl_pct"] for t in trades if not t["win"]]
    
    avg_win = np.mean(winning_pnls) if winning_pnls else 0.0
    avg_loss = np.mean(losing_pnls) if losing_pnls else 0.0
    largest_win = max(winning_pnls) if winning_pnls else 0.0
    largest_loss = min(losing_pnls) if losing_pnls else 0.0
    
    gross_profit = sum(t["pnl_vnd"] for t in trades if t["win"])
    gross_loss = abs(sum(t["pnl_vnd"] for t in trades if not t["win"]))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")
    
    # Holding period stats
    holding_days = [t["holding_days"] for t in trades]
    avg_hold = np.mean(holding_days)
    max_hold = max(holding_days)
    min_hold = min(holding_days)
    
    # Kelly overall
    kelly = calculate_kelly(trades)
    
    print("\n" + "=" * 100)
    print(" 📊 FINVISTA PORTFOLIO OPTIMIZATION & ADVANCED TRADING STATISTICS")
    print("=" * 100)
    print(f" Tài khoản: {username.upper()} | Nguồn dữ liệu: {source_label}")
    print(f" Thời gian: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 100)
    
    # ── SECTION 2: TRANSACTION SUMMARY ──
    print("\n" + "-" * 100)
    print(" [1] TỔNG QUAN GIAO DỊCH (Transaction Summary)")
    print("-" * 100)
    
    pf_str = f"{profit_factor:.2f}" if profit_factor != float("inf") else "∞"
    sign = "+" if total_pnl_vnd >= 0 else ""
    
    print(f"  Tổng số lệnh hoàn tất  : {total:>5}        |  Tỷ lệ thắng (Win Rate) : {win_rate:.1f}%")
    print(f"  Số lệnh thắng          : {wins:>5}        |  Profit Factor          : {pf_str}")
    print(f"  Số lệnh thua           : {losses:>5}        |  Kelly Criterion (Full) : {kelly['kelly_full']:+.1f}%")
    print(f"  Tổng phí giao dịch     : {total_fees:>12,.0f}đ  |  Kelly Criterion (Half) : {kelly['kelly_half']:+.1f}%")
    print(f"  Lợi nhuận ròng (P/L)   : {sign}{total_pnl_vnd:>12,.0f}đ  |  Payoff Ratio           : {kelly['payoff_ratio']:.2f}")
    
    # ── SECTION 3: PROFIT/LOSS ANALYSIS ──
    print("\n" + "-" * 100)
    print(" [2] PHÂN TÍCH LỢI NHUẬN (Profit/Loss Analysis)")
    print("-" * 100)
    print(f"  Trung bình lệnh thắng  : {avg_win:>+8.2f}%      |  Lệnh thắng lớn nhất    : {largest_win:>+8.2f}%")
    print(f"  Trung bình lệnh thua   : {avg_loss:>+8.2f}%      |  Lệnh thua lớn nhất     : {largest_loss:>+8.2f}%")
    print(f"  Tổng lãi gộp (Gross)   : {gross_profit:>12,.0f}đ  |  Tổng lỗ gộp (Gross)    : -{gross_loss:>11,.0f}đ")
    
    # ── SECTION 4: HOLDING PERIOD ANALYSIS ──
    print("\n" + "-" * 100)
    print(" [3] PHÂN TÍCH THỜI GIAN NẮM GIỮ (Holding Period)")
    print("-" * 100)
    print(f"  Trung bình giữ lệnh    : {avg_hold:>5.1f} ngày    |  Lệnh giữ lâu nhất      : {max_hold:>3} ngày")
    print(f"  Lệnh giữ ngắn nhất     : {min_hold:>5} ngày    |  Tổng ngày giao dịch    : {sum(holding_days):>3} ngày")
    
    # ── SECTION 5: EXIT REASON ANALYSIS ──
    print("\n" + "-" * 100)
    print(" [4] PHÂN TÍCH THEO LÝ DO THOÁT LỆNH (Exit Reason Breakdown)")
    print("-" * 100)
    
    exit_stats = analyze_exit_reasons(trades)
    print(f"  {'Lý Do Thoát':<25} | {'Số Lệnh':>8} | {'Thắng':>6} | {'Thua':>6} | {'Win Rate':>8} | {'P/L TB':>8} | {'Tổng P/L (VND)':>16}")
    print("  " + "-" * 95)
    for ex in exit_stats:
        pnl_sign = "+" if ex["total_pnl_vnd"] >= 0 else ""
        print(f"  {ex['category']:<25} | {ex['count']:>8} | {ex['wins']:>6} | {ex['losses']:>6} | {ex['win_rate']:>7.1f}% | {ex['avg_pnl']:>+7.1f}% | {pnl_sign}{ex['total_pnl_vnd']:>15,.0f}đ")
    
    # ── SECTION 6: PERFORMANCE BY UNDERLYING ──
    print("\n" + "-" * 100)
    print(" [5] HIỆU SUẤT THEO CỔ PHIẾU CƠ SỞ (Performance by Underlying)")
    print("-" * 100)
    
    kelly_by_ul = calculate_kelly_by_underlying(trades)
    print(f"  {'Cổ Phiếu CS':<10} | {'Lệnh':>5} | {'Thắng':>5} | {'Thua':>5} | {'Win Rate':>8} | {'P/L TB':>8} | {'Kelly (Full)':>12} | {'Kelly (Half)':>12} | {'Khuyến Nghị':<20}")
    print("  " + "-" * 95)
    for k in kelly_by_ul:
        # Recommendation based on Kelly
        if k["kelly_half"] >= 15:
            rec = "TĂNG TỈ TRỌNG"
        elif k["kelly_half"] >= 5:
            rec = "GIỮ NGUYÊN"
        elif k["kelly_half"] >= 0:
            rec = "GIẢM TỈ TRỌNG"
        else:
            rec = "NGỪNG GIAO DỊCH"
        
        print(f"  {k['underlying']:<10} | {k['total_trades']:>5} | {k['wins']:>5} | {k['losses']:>5} | {k['win_rate']:>7.1f}% | {k['avg_win']:>+7.1f}% | {k['kelly_full']:>+11.1f}% | {k['kelly_half']:>+11.1f}% | {rec:<20}")
    
    # ── SECTION 7: MEAN-VARIANCE OPTIMIZATION ──
    print("\n" + "-" * 100)
    print(" [6] TỐI ƯU HÓA DANH MỤC MEAN-VARIANCE (Efficient Frontier Allocation)")
    print("-" * 100)
    
    mv = mean_variance_optimize(trades)
    
    if mv["weights"]:
        print(f"  Lợi nhuận kỳ vọng danh mục : {mv['expected_return']:+.2f}%")
        print(f"  Rủi ro danh mục (Std Dev)   : {mv['portfolio_vol']:.2f}%")
        print(f"  Sharpe tối ưu (Monte Carlo) : {mv['sharpe']:.2f}")
        print()
        print(f"  {'Cổ Phiếu CS':<12} | {'Tỉ Trọng Tối Ưu':>15} | {'Phân Bổ Vốn (100Tr)':>20}")
        print("  " + "-" * 55)
        for u, w in sorted(mv["weights"].items(), key=lambda x: x[1], reverse=True):
            alloc_vnd = initial_cash * w / 100
            bar = "█" * int(w / 3)
            print(f"  {u:<12} | {w:>14.1f}% | {alloc_vnd:>17,.0f}đ  {bar}")
    else:
        print("  ⚠️ Chưa đủ dữ liệu đa dạng hóa để tối ưu Mean-Variance (cần >= 2 underlying).")

    # ── SECTION 8: INDUSTRY CONCENTRATION ──
    print("\n" + "-" * 100)
    print(" [7] PHÂN TÍCH RỦI RO NGÀNH (Industry Concentration - Elton & Gruber MPT)")
    print("-" * 100)
    from src.modules.cw_pricing.backtest.industry_analyzer import IndustryAnalyzer
    analyzer = IndustryAnalyzer()
    concentration = analyzer.get_industry_concentration(trades)
    
    if concentration:
        print(f"  {'Ngành':<25} | {'Tỉ Trọng Lệnh (%)':>15} | {'Đánh giá Rủi ro':<20}")
        print("  " + "-" * 65)
        for industry, pct in sorted(concentration.items(), key=lambda x: x[1], reverse=True):
            risk_level = "ỔN ĐỊNH"
            if pct > 40: risk_level = "⚠️ TẬP TRUNG CAO"
            if pct > 60: risk_level = "🚨 RỦI RO HỆ THỐNG"
            print(f"  {industry:<25} | {pct:>15.1f}% | {risk_level:<20}")
    else:
        print("  ⚠️ Không có dữ liệu để phân tích ngành.")
    
    # ── FOOTER ──
    print("\n" + "=" * 100)
    print(" Hệ thống Định Lượng Finvista | Portfolio Optimization Engine v1.0")
    print("=" * 100 + "\n")


if __name__ == "__main__":
    print_advanced_stats()
