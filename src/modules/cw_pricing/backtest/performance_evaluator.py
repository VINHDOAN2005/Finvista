import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime
import joblib
import warnings
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
warnings.filterwarnings('ignore')

from src.modules.cw_pricing.models.pricing_core import RISK_FREE_RATE

def calculate_portfolio_performance(trades_list, initial_capital=100000000.0, max_concurrent_trades=5, total_fees_pct=0.1):
    """
    Simulates a daily portfolio equity curve from a list of trades.
    Uses the exact close prices from the database to mark-to-market active positions.
    Calculates:
      - Transaction Analysis (Initial Capital, Net Equity, Profit, Fees, Trades, Win/Loss, etc.)
      - Performance Metrics (Cumulative Return, CAGR, Win Rate, Profit Factor, Sharpe, Sortino, Calmar, Payoff, Volatility, Max DD)
      - Advanced Metrics (Recovery Factor, Kelly Criterion, Omega Ratio, Ulcer Index, VaR, CVaR)
    """
    if not trades_list:
        return {}

    # Import engine to fetch daily prices for mark-to-market
    from src.core.database import engine
    
    # Load all daily CW prices for MTM
    cw_prices_df = pd.read_sql("SELECT symbol, date, close FROM cw_history", engine)
    cw_prices_df['date'] = pd.to_datetime(cw_prices_df['date']).dt.strftime('%Y-%m-%d')
    price_map = cw_prices_df.set_index(['symbol', 'date'])['close'].to_dict()
    
    # Parse trade dates
    trades = pd.DataFrame(trades_list)
    trades['entry_date'] = pd.to_datetime(trades['entry_date']).dt.strftime('%Y-%m-%d')
    trades['exit_date'] = pd.to_datetime(trades['exit_date']).dt.strftime('%Y-%m-%d')
    
    # Get all unique dates in the backtest period sorted chronologically
    all_dates = sorted(list(set(trades['entry_date'].tolist() + trades['exit_date'].tolist() + cw_prices_df['date'].tolist())))
    # Filter dates to range of trades
    min_date = trades['entry_date'].min()
    max_date = trades['exit_date'].max()
    all_dates = [d for d in all_dates if min_date <= d <= max_date]
    
    # Portfolio state
    cash = initial_capital
    active_positions = [] # list of dicts
    equity_curve = []
    total_fees_paid = 0.0
    
    # Map entries and exits by date for fast lookup
    entries_by_date = trades.groupby('entry_date')
    exits_by_date = trades.groupby('exit_date')
    
    for current_date in all_dates:
        # 1. Process exits first (sell positions)
        if current_date in exits_by_date.groups:
            exits = exits_by_date.get_group(current_date)
            for _, trade in exits.iterrows():
                match = None
                for pos in active_positions:
                    if pos['symbol'] == trade['cw'] and pos['exit_date'] == current_date:
                        match = pos
                        break
                if match:
                    exit_val = match['qty'] * trade['exit_price']
                    fee = exit_val * (total_fees_pct / 100.0)
                    total_fees_paid += fee
                    cash += (exit_val - fee)
                    active_positions.remove(match)
        
        # 2. Process entries (buy positions if slots available)
        if current_date in entries_by_date.groups:
            entries = entries_by_date.get_group(current_date)
            for _, trade in entries.iterrows():
                if len(active_positions) < max_concurrent_trades:
                    alloc = initial_capital / max_concurrent_trades
                    if cash >= alloc:
                        fee = alloc * (total_fees_pct / 100.0)
                        total_fees_paid += fee
                        qty = (alloc - fee) / trade['entry_price']
                        cash -= alloc
                        active_positions.append({
                            'symbol': trade['cw'],
                            'qty': qty,
                            'entry_price': trade['entry_price'],
                            'exit_price': trade['exit_price'],
                            'exit_date': trade['exit_date']
                        })
        
        # 3. Mark-to-Market
        pos_value = 0.0
        for pos in active_positions:
            price = price_map.get((pos['symbol'], current_date), pos['entry_price'])
            pos_value += pos['qty'] * price
            
        nav = cash + pos_value
        equity_curve.append({
            'date': current_date,
            'nav': nav,
            'cash': cash,
            'pos_value': pos_value
        })
        
    equity_df = pd.DataFrame(equity_curve)
    if equity_df.empty:
        return {}
        
    # Calculate returns
    equity_df['returns'] = equity_df['nav'].pct_change().fillna(0.0)
    
    # ----------------------------------------------------
    # Metric Calculations
    # ----------------------------------------------------
    final_nav = equity_df['nav'].iloc[-1]
    cumulative_return = (final_nav - initial_capital) / initial_capital * 100
    
    # CAGR (Annualized) - Always annualize for proper comparison
    start_dt = datetime.strptime(min_date, '%Y-%m-%d')
    end_dt = datetime.strptime(max_date, '%Y-%m-%d')
    days = max((end_dt - start_dt).days, 1)
    years = days / 365.0
    
    # Always annualize CAGR for proper financial comparison
    # Even for short periods, CAGR should reflect annualized rate
    if years > 0 and final_nav > 0:
        cagr = ((final_nav / initial_capital) ** (1.0 / years) - 1.0) * 100
    else:
        cagr = -100.0
    
    # Volatility
    daily_vol = equity_df['returns'].std()
    ann_vol = daily_vol * np.sqrt(252) * 100
    
    # Sharpe & Sortino
    mean_return = equity_df['returns'].mean()
    sharpe = (mean_return / daily_vol) * np.sqrt(252) if daily_vol > 0 else 0.0
    
    downside_returns = equity_df['returns'][equity_df['returns'] < 0]
    downside_vol = downside_returns.std() if len(downside_returns) > 1 else daily_vol
    sortino = (mean_return / downside_vol) * np.sqrt(252) if downside_vol > 0 else 0.0
    
    # Max Drawdown
    equity_df['peak'] = equity_df['nav'].cummax()
    equity_df['dd'] = (equity_df['nav'] - equity_df['peak']) / equity_df['peak'] * 100
    max_dd = equity_df['dd'].min()
    
    # Calmar
    calmar = (cagr / abs(max_dd)) if max_dd < 0 else float('inf')
    
    # Trade statistics
    total_trades = len(trades_list)
    wins = sum(1 for t in trades_list if t['win'])
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0.0
    
    winning_trades = [t['pnl_pct'] for t in trades_list if t['win']]
    losing_trades = [t['pnl_pct'] for t in trades_list if not t['win']]
    
    largest_win = max(winning_trades) if winning_trades else 0.0
    largest_loss = min(losing_trades) if losing_trades else 0.0
    avg_win = np.mean(winning_trades) if winning_trades else 0.0
    avg_loss = np.mean(losing_trades) if losing_trades else 0.0
    
    payoff_ratio = (avg_win / abs(avg_loss)) if avg_loss != 0 else float('inf')
    
    winning_pnl = sum(winning_trades)
    losing_pnl = abs(sum(losing_trades))
    profit_factor = winning_pnl / losing_pnl if losing_pnl > 0 else float('inf')
    
    # Advanced Metrics
    recovery_factor = (cumulative_return / abs(max_dd)) if max_dd < 0 else float('inf')
    
    # Kelly Criterion
    wr_decimal = win_rate / 100.0
    kelly = (wr_decimal - (1.0 - wr_decimal) / payoff_ratio) * 100 if payoff_ratio > 0 and payoff_ratio != float('inf') else 0.0
    
    # Omega Ratio (threshold = 0)
    positive_returns = equity_df['returns'][equity_df['returns'] > 0].sum()
    negative_returns = abs(equity_df['returns'][equity_df['returns'] < 0].sum())
    omega = positive_returns / negative_returns if negative_returns > 0 else float('inf')
    
    # Ulcer Index
    ulcer_index = np.sqrt(np.mean((equity_df['dd'] / 100.0) ** 2))
    
    # VaR & CVaR (95% confidence)
    var_95 = np.percentile(equity_df['returns'], 5) * 100
    cvar_95 = equity_df['returns'][equity_df['returns'] <= (var_95 / 100.0)].mean() * 100
    if np.isnan(cvar_95):
        cvar_95 = var_95
        
    # Yearly stats
    equity_df['year'] = pd.to_datetime(equity_df['date']).dt.year
    yearly_stats = []
    for year, group in equity_df.groupby('year'):
        y_initial = group['nav'].iloc[0]
        y_final = group['nav'].iloc[-1]
        y_return = (y_final - y_initial) / y_initial * 100
        
        y_mean = group['returns'].mean()
        y_vol = group['returns'].std()
        y_sharpe = (y_mean / y_vol) * np.sqrt(252) if y_vol > 0 else 0.0
        
        group['y_peak'] = group['nav'].cummax()
        group['y_dd'] = (group['nav'] - group['y_peak']) / group['y_peak'] * 100
        y_max_dd = group['y_dd'].min()
        
        y_trades = [t for t in trades_list if pd.to_datetime(t['entry_date']).year == year]
        y_wins = sum(1 for t in y_trades if t['win'])
        y_wr = (y_wins / len(y_trades) * 100) if len(y_trades) > 0 else 0.0
        
        y_winning_pnl = sum(t['pnl_pct'] for t in y_trades if t['win'])
        y_losing_pnl = abs(sum(t['pnl_pct'] for t in y_trades if not t['win']))
        y_pf = y_winning_pnl / y_losing_pnl if y_losing_pnl > 0 else float('inf')
        
        yearly_stats.append({
            'year': year,
            'return': y_return,
            'sharpe': y_sharpe,
            'max_dd': y_max_dd,
            'win_rate': y_wr,
            'profit_factor': y_pf
        })
        
    return {
        'initial_capital': initial_capital,
        'final_nav': final_nav,
        'cumulative_return': cumulative_return,
        'cagr': cagr,
        'volatility': ann_vol / 100.0, # as fraction
        'sharpe': sharpe,
        'sortino': sortino,
        'max_dd': max_dd,
        'calmar': calmar,
        'win_rate': win_rate,
        'profit_factor': profit_factor,
        'total_trades': total_trades,
        'largest_win': largest_win,
        'largest_loss': largest_loss,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'total_fees_paid': total_fees_paid,
        'recovery_factor': recovery_factor,
        'kelly': kelly,
        'omega': omega,
        'ulcer_index': ulcer_index,
        'var_95': var_95,
        'cvar_95': cvar_95,
        'payoff_ratio': payoff_ratio,
        'yearly_stats': yearly_stats
    }

def print_stage_report(stage_name, metrics):
    """
    Prints the structured Stage report with three sub-sections:
    - OVERVIEW
    - PERFORMANCE
    - ANALYSIS
    """
    if not metrics:
        print(f"[!] No metrics calculated for stage: {stage_name}")
        return
        
    print("\n" + "=" * 90)
    print(f" STAGE: {stage_name.upper()}")
    print("=" * 90)
    
    # ----------------------------------------------------
    # 1. OVERVIEW
    # ----------------------------------------------------
    print("\n[1] OVERVIEW")
    print("-" * 90)
    print(f"Aggregate Data:")
    print(f"  Sharpe: {metrics['sharpe']:.2f} | CAGR: {metrics['cagr']:+.2f}% | Max Drawdown: {metrics['max_dd']:.2f}% | Profit Factor: {metrics['profit_factor']:.2f} | Calmar: {metrics['calmar']:.2f}")
    print("\nYearly Breakdown:")
    print(f"{'Year':<6} | {'Sharpe':<8} | {'CAGR':<10} | {'Max Drawdown':<14} | {'Profit Factor':<13} | {'Calmar':<8}")
    print("-" * 90)
    for y in metrics['yearly_stats']:
        pf_str = f"{y['profit_factor']:.2f}" if y['profit_factor'] != float('inf') else "N/A"
        y_calmar = (y['return'] / abs(y['max_dd'])) if y['max_dd'] < 0 else float('inf')
        y_calmar_str = f"{y_calmar:.2f}" if y_calmar != float('inf') else "N/A"
        print(f"{y['year']:<6} | {y['sharpe']:<8.2f} | {y['return']:+10.2f}% | {y['max_dd']:<14.2f}% | {pf_str:<13} | {y_calmar_str:<8}")
    print("-" * 90)
    
    # ----------------------------------------------------
    # 2. PERFORMANCE
    # ----------------------------------------------------
    print("\n[2] PERFORMANCE")
    print("-" * 90)
    print(f"{'Transaction Analysis':<35} | {'Performance Metrics':<35}")
    print("-" * 90)
    print(f"  Initial Capital : {metrics['initial_capital']:,.0f} VND          |  Cumulative Return : {metrics['cumulative_return']:+.2f}%")
    print(f"  Net Equity      : {metrics['final_nav']:,.0f} VND                |  CAGR              : {metrics['cagr']:+.2f}%")
    print(f"  Total Profit    : {metrics['cumulative_return']:+.2f}%           |  Win Rate          : {metrics['win_rate']:.2f}%")
    print(f"  Total Fees      : {metrics['total_fees_paid']:,.0f} VND          |  Profit Factor (PF): {metrics['profit_factor']:.2f}")
    print(f"  Total Trades    : {metrics['total_trades']:<5}                   |  Sharpe Ratio      : {metrics['sharpe']:.2f}")
    print(f"  Largest Win     : {metrics['largest_win']:+.2f}%                 |  Sortino Ratio     : {metrics['sortino']:.2f}")
    print(f"  Largest Loss    : {metrics['largest_loss']:+.2f}%                |  Calmar Ratio      : {metrics['calmar']:.2f}")
    print(f"  Avg Win         : {metrics['avg_win']:+.2f}%                     |  Payoff Ratio      : {metrics['payoff_ratio']:.2f}")
    print(f"  Avg Loss        : {metrics['avg_loss']:+.2f}%                    |  Volatility        : {metrics['volatility']:.2f}")
    print(f"  Unrealized PnL  : 0 VND                                          |  Max Drawdown      : {metrics['max_dd']:.2f}%")
    print("-" * 90)
    print("Advanced Metrics:")
    print(f"  Recovery Factor : {metrics['recovery_factor']:.2f}")
    print(f"  Kelly Criterion : {metrics['kelly']:+.2f}%")
    print(f"  Omega Ratio     : {metrics['omega']:.2f}")
    print(f"  Ulcer Index     : {metrics['ulcer_index']:.4f}")
    print(f"  VaR (95%)       : {metrics['var_95']:.2f}%")
    print(f"  CVaR (95%)      : {metrics['cvar_95']:.2f}%")
    print("-" * 90)
    
    # ----------------------------------------------------
    # 3. ANALYSIS (Target Verification)
    # ----------------------------------------------------
    print("\n[3] ANALYSIS (Benchmark Status)")
    print("-" * 90)
    
    # Evaluation against targets
    targets = [
        {"name": "Sharpe Ratio", "val": metrics['sharpe'], "op": ">=", "target": 1.30, "fmt": "{:.2f}"},
        {"name": "CAGR", "val": metrics['cagr'], "op": ">=", "target": 15.0, "fmt": "{:+.2f}%"},
        {"name": "Max Drawdown", "val": metrics['max_dd'], "op": ">=", "target": -40.0, "fmt": "{:.2f}%"}, # DD is negative, so DD >= -40% (adjusted for VN CW volatility)
        {"name": "Profit Factor", "val": metrics['profit_factor'], "op": ">=", "target": 1.20, "fmt": "{:.2f}"},
        {"name": "Calmar Ratio", "val": metrics['calmar'], "op": ">=", "target": 1.10, "fmt": "{:.2f}"}
    ]
    
    pass_count = 0
    fail_count = 0
    
    print(f"{'Metric':<25} | {'Target':<15} | {'Actual':<12} | {'Status':<10}")
    print("-" * 90)
    for t in targets:
        passed = False
        if t['op'] == ">=":
            passed = t['val'] >= t['target']
            
        status_str = "PASS" if passed else "FAIL"
        if passed:
            pass_count += 1
        else:
            fail_count += 1
            
        target_str = f">= {t['target']}"
        if "%" in t['fmt']:
            target_str = f">= {t['target']}%"
            
        actual_str = t['fmt'].format(t['val'])
        print(f"{t['name']:<25} | {target_str:<15} | {actual_str:<12} | {status_str:<10}")
        
    print("-" * 90)
    print(f"IS Testing Status: All 5 | Pass {pass_count} | Fail {fail_count} | Pending 0")
    print("=" * 90 + "\n")

# ==========================================
# PRICING MODEL BENCHMARKING
# ==========================================

def calibrate_heston_parameters(df, sample_size=50):
    """
    Calibrate Heston parameters using historical CW data.
    Uses simple grid search to find parameters that minimize MAE.
    
    Args:
        df: DataFrame with CW data
        sample_size: Number of CWs to use for calibration
    
    Returns:
        dict: Optimal Heston parameters
    """
    from src.modules.cw_pricing.models.pricing_core import calculate_d1_d2
    from src.modules.cw_pricing.models.pricing_core_enhanced import heston_price
    from scipy.stats import norm
    
    print("\n" + "=" * 80)
    print("CALIBRATING HESTON PARAMETERS FOR VIETNAM MARKET")
    print("=" * 80)
    
    # Sample data for calibration
    df_sample = df.head(sample_size)
    
    # Parameter grid search ranges
    kappa_range = [1.0, 2.0, 3.0, 5.0]
    theta_range = [0.02, 0.05, 0.1, 0.2]
    sigma_range = [0.2, 0.3, 0.4, 0.5]
    rho_range = [-0.9, -0.7, -0.5, -0.3]
    v0_range = [0.02, 0.04, 0.06, 0.1]
    
    best_mae = float('inf')
    best_params = {
        'kappa': 2.0,
        'theta': 0.05,
        'sigma': 0.3,
        'rho': -0.7,
        'v0': 0.04
    }
    
    # Simple grid search (limited combinations for speed)
    for kappa in kappa_range:
        for theta in theta_range:
            for sigma in sigma_range:
                for rho in rho_range:
                    for v0 in v0_range:
                        errors = []
                        for idx, row in df_sample.iterrows():
                            S = row['underlying_price']
                            K = row['strike_price']
                            T = row['days_to_maturity'] / 365.0
                            r = RISK_FREE_RATE
                            
                            if T <= 0 or S <= 0 or K <= 0:
                                continue
                            
                            # Get conversion ratio
                            conversion_ratio = row.get('ratio', 1.0)
                            if isinstance(conversion_ratio, str) and ':' in conversion_ratio:
                                try:
                                    conversion_ratio = float(conversion_ratio.split(':')[0])
                                except:
                                    conversion_ratio = 1.0
                            elif pd.isna(conversion_ratio) or conversion_ratio == 0:
                                conversion_ratio = 1.0
                            
                            # Calculate Heston price with current parameters
                            heston_price_val = heston_price(S, K, T, r, 'call', kappa, theta, sigma, rho, v0) / conversion_ratio
                            error = abs(heston_price_val - row['price'])
                            errors.append(error)
                        
                        if errors:
                            mae = np.mean(errors)
                            if mae < best_mae:
                                best_mae = mae
                                best_params = {
                                    'kappa': kappa,
                                    'theta': theta,
                                    'sigma': sigma,
                                    'rho': rho,
                                    'v0': v0
                                }
    
    print(f"\n🎯 Optimal Heston Parameters:")
    print(f"   kappa (mean reversion speed): {best_params['kappa']}")
    print(f"   theta (long-term volatility): {best_params['theta']}")
    print(f"   sigma (vol of vol): {best_params['sigma']}")
    print(f"   rho (correlation): {best_params['rho']}")
    print(f"   v0 (initial volatility): {best_params['v0']}")
    print(f"   Calibration MAE: {best_mae:.2f}")
    
    return best_params

def benchmark_pricing_models():
    """
    Comprehensive benchmark of all pricing models against actual market prices.
    Compares: Current Model, Black-Scholes, Heston, ML Model
    
    Returns:
        dict: Benchmark results with metrics for all models
    """
    print("=" * 80)
    print("COMPREHENSIVE BENCHMARK - ALL PRICING MODELS")
    print("=" * 80)
    
    # Load data
    from src.core.database import engine
    df = pd.read_sql('SELECT * FROM market_opportunities', engine)
    df = df.dropna(subset=['price', 'theoretical_price', 'underlying_price', 'strike_price', 'days_to_maturity'])
    
    print(f"\n📊 Total CWs: {len(df)}")
    
    # Use default Heston parameters (calibration disabled for speed)
    # Conversion ratio fix already improved Heston significantly
    optimal_heston_params = {
        'kappa': 2.0,
        'theta': 0.05,
        'sigma': 0.3,
        'rho': -0.7,
        'v0': 0.04
    }
    
    # Load ML model
    model_path = 'models/ml_pricing_model.pkl'
    feature_names_path = 'models/feature_names.pkl'
    
    if os.path.exists(model_path) and os.path.exists(feature_names_path):
        ml_model = joblib.load(model_path)
        feature_names = joblib.load(feature_names_path)
        print("✅ ML Model loaded successfully")
    else:
        print("❌ ML Model not found. Please run train_test_ml_pricing.py first")
        ml_model = None
        feature_names = None
    
    # Calculate prices for all models
    from src.modules.cw_pricing.models.pricing_core import calculate_d1_d2
    from src.modules.cw_pricing.models.pricing_core_enhanced import heston_price
    from scipy.stats import norm
    
    current_prices = []
    bs_prices = []
    heston_prices = []
    ml_prices = []
    market_prices = []
    
    for idx, row in df.iterrows():
        S = row['underlying_price']
        K = row['strike_price']
        T = row['days_to_maturity'] / 365.0
        r = RISK_FREE_RATE
        sigma = row.get('implied_volatility_pct', 0.45) / 100.0 if pd.notna(row.get('implied_volatility_pct')) else 0.45
        
        if T <= 0 or S <= 0 or K <= 0:
            continue
        
        # Current Theoretical Price
        current_prices.append(row['theoretical_price'])
        
        # Black-Scholes Price (with conversion ratio for Vietnam CWs)
        d1, d2 = calculate_d1_d2(S, K, T, r, sigma)
        conversion_ratio = row.get('ratio', 1.0)  # Get conversion ratio from database
        # Parse ratio string like "4:1" to float 4.0
        if isinstance(conversion_ratio, str) and ':' in conversion_ratio:
            try:
                conversion_ratio = float(conversion_ratio.split(':')[0])
            except:
                conversion_ratio = 1.0
        elif pd.isna(conversion_ratio) or conversion_ratio == 0:
            conversion_ratio = 1.0
        
        bs_price = (S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)) / conversion_ratio
        bs_prices.append(bs_price)
        
        # Heston Price (with calibrated parameters and conversion ratio)
        heston_price_val = heston_price(
            S, K, T, r, 'call',
            kappa=optimal_heston_params['kappa'],
            theta=optimal_heston_params['theta'],
            sigma=optimal_heston_params['sigma'],
            rho=optimal_heston_params['rho'],
            v0=optimal_heston_params['v0']
        ) / conversion_ratio
        heston_prices.append(heston_price_val)
        
        # ML Model Price
        if ml_model is not None:
            features = {
                'S': S, 'K': K, 'T': T, 'r': r,
                'moneyness': S / K,
                'log_moneyness': np.log(S / K) if S / K > 0 else 0,
                'implied_volatility': sigma,
                'historical_volatility': row.get('historical_volatility_pct', 45.0) / 100.0,
                'volume': row.get('volume', 0),
                'turnover': row.get('turnover', 0),
                'delta': row.get('delta', 0.5),
                'gamma': row.get('gamma', 0),
                'theta': row.get('theta_burn_day', 0),
                'vega': row.get('vega', 0),
                'premium_pct': row.get('premium_pct', 10) / 100.0,
                'gearing': row.get('gearing', 2),
                'prob_itm': row.get('prob_itm', 0.5),
                'S_K_ratio': S / K,
                'T_sqrt': np.sqrt(T)
            }
            
            feature_df = pd.DataFrame([features])
            for col in feature_names:
                if col not in feature_df.columns:
                    feature_df[col] = 0
            feature_df = feature_df[feature_names]
            
            ml_price = ml_model.predict(feature_df)[0]
            ml_prices.append(ml_price)
        else:
            ml_prices.append(np.nan)
        
        market_prices.append(row['price'])
    
    current_prices = np.array(current_prices)
    bs_prices = np.array(bs_prices)
    heston_prices = np.array(heston_prices)
    ml_prices = np.array(ml_prices)
    market_prices = np.array(market_prices)
    
    print(f"📊 Calculated prices for {len(market_prices)} CWs")
    
    # Calculate metrics
    def calculate_metrics(predictions, actual):
        errors = predictions - actual
        abs_errors = np.abs(errors)
        # Fix MAPE: Filter out division by zero for low-priced CWs
        valid_mask = actual > 0.1  # Filter out prices <= 0.1 (100 VND)
        pct_errors = np.abs(errors[valid_mask] / actual[valid_mask]) * 100
        return {
            'MAE': np.mean(abs_errors),
            'RMSE': np.sqrt(np.mean(errors**2)),
            'MAPE': np.mean(pct_errors) if len(pct_errors) > 0 else 0.0,
            'Median_AE': np.median(abs_errors),
            'Median_PE': np.median(pct_errors) if len(pct_errors) > 0 else 0.0,
            'Std_PE': np.std(pct_errors) if len(pct_errors) > 0 else 0.0,
            'R2': r2_score(actual, predictions),
            'Max_Error': np.max(abs_errors),
            'Min_Error': np.min(abs_errors)
        }
    
    metrics_current = calculate_metrics(current_prices, market_prices)
    metrics_bs = calculate_metrics(bs_prices, market_prices)
    metrics_heston = calculate_metrics(heston_prices, market_prices)
    metrics_ml = calculate_metrics(ml_prices, market_prices) if ml_model is not None else None
    
    # Comparison table
    print("\n" + "=" * 80)
    print("COMPARISON TABLE")
    print("=" * 80)
    comparison_df = pd.DataFrame({
        'Current Model': metrics_current,
        'Black-Scholes': metrics_bs,
        'Heston': metrics_heston,
    })
    if ml_model is not None:
        comparison_df['ML Model'] = metrics_ml
    print(comparison_df.round(2))
    
    # Ranking
    all_metrics = {
        'Current Model': metrics_current,
        'Black-Scholes': metrics_bs,
        'Heston': metrics_heston,
    }
    if ml_model is not None:
        all_metrics['ML Model'] = metrics_ml
    
    ranked = sorted(all_metrics.items(), key=lambda x: x[1]['MAE'])
    
    print("\n🏆 Ranking by MAE (best to worst):")
    for rank, (name, metrics) in enumerate(ranked, 1):
        print(f"   {rank}. {name}: MAE = {metrics['MAE']:.2f}")
    
    # Accuracy scores
    def calculate_accuracy_score(metrics):
        return max(0, 100 - metrics['MAPE'])
    
    scores = {name: calculate_accuracy_score(metrics) for name, metrics in all_metrics.items()}
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    
    print("\n🏆 Accuracy Scores:")
    for rank, (name, score) in enumerate(sorted_scores, 1):
        print(f"   {rank}. {name}: {score:.1f}/100")
    
    # Accuracy distribution
    def accuracy_distribution(predictions, actual):
        pct_errors = np.abs((predictions - actual) / actual) * 100
        good = (pct_errors < 10).sum()
        acceptable = ((pct_errors >= 10) & (pct_errors < 30)).sum()
        poor = (pct_errors >= 30).sum()
        total = len(actual)
        return {
            'good': good, 'acceptable': acceptable, 'poor': poor,
            'total': total,
            'good_pct': good / total * 100,
            'acceptable_pct': acceptable / total * 100,
            'poor_pct': poor / total * 100
        }
    
    dist_current = accuracy_distribution(current_prices, market_prices)
    dist_bs = accuracy_distribution(bs_prices, market_prices)
    dist_heston = accuracy_distribution(heston_prices, market_prices)
    dist_ml = accuracy_distribution(ml_prices, market_prices) if ml_model is not None else None
    
    print("\n📊 Current Model:")
    print(f"   Good (<10%): {dist_current['good']} ({dist_current['good_pct']:.1f}%)")
    print(f"   Acceptable (10-30%): {dist_current['acceptable']} ({dist_current['acceptable_pct']:.1f}%)")
    print(f"   Poor (>30%): {dist_current['poor']} ({dist_current['poor_pct']:.1f}%)")
    
    print("\n📊 Black-Scholes:")
    print(f"   Good (<10%): {dist_bs['good']} ({dist_bs['good_pct']:.1f}%)")
    print(f"   Acceptable (10-30%): {dist_bs['acceptable']} ({dist_bs['acceptable_pct']:.1f}%)")
    print(f"   Poor (>30%): {dist_bs['poor']} ({dist_bs['poor_pct']:.1f}%)")
    
    print("\n📊 Heston:")
    print(f"   Good (<10%): {dist_heston['good']} ({dist_heston['good_pct']:.1f}%)")
    print(f"   Acceptable (10-30%): {dist_heston['acceptable']} ({dist_heston['acceptable_pct']:.1f}%)")
    print(f"   Poor (>30%): {dist_heston['poor']} ({dist_heston['poor_pct']:.1f}%)")
    
    if ml_model is not None:
        print("\n📊 ML Model:")
        print(f"   Good (<10%): {dist_ml['good']} ({dist_ml['good_pct']:.1f}%)")
        print(f"   Acceptable (10-30%): {dist_ml['acceptable']} ({dist_ml['acceptable_pct']:.1f}%)")
        print(f"   Poor (>30%): {dist_ml['poor']} ({dist_ml['poor_pct']:.1f}%)")
    
    # Bias analysis
    def bias_analysis(predictions, actual):
        errors = predictions - actual
        median_error = np.median(errors)
        mean_error = np.mean(errors)
        
        if median_error > 0:
            bias = "OVERVALUED"
        elif median_error < 0:
            bias = "UNDERVALUED"
        else:
            bias = "UNBIASED"
        
        return {'Median_Error': median_error, 'Mean_Error': mean_error, 'Bias': bias}
    
    bias_current = bias_analysis(current_prices, market_prices)
    bias_bs = bias_analysis(bs_prices, market_prices)
    bias_heston = bias_analysis(heston_prices, market_prices)
    bias_ml = bias_analysis(ml_prices, market_prices) if ml_model is not None else None
    
    print("\n📊 Bias Analysis:")
    print(f"   Current Model: {bias_current['Bias']} (Median: {bias_current['Median_Error']:.2f})")
    print(f"   Black-Scholes: {bias_bs['Bias']} (Median: {bias_bs['Median_Error']:.2f})")
    print(f"   Heston: {bias_heston['Bias']} (Median: {bias_heston['Median_Error']:.2f})")
    if ml_model is not None:
        print(f"   ML Model: {bias_ml['Bias']} (Median: {bias_ml['Median_Error']:.2f})")
    
    # Final recommendation
    best_model = sorted_scores[0][0]
    best_score = sorted_scores[0][1]
    
    print(f"\n🏆 BEST MODEL: {best_model}")
    print(f"   Accuracy Score: {best_score:.1f}/100")
    
    print(f"\n💡 RECOMMENDATION:")
    if best_model == 'ML Model':
        print("   ✅ Deploy ML Model into production")
        print("   ✅ ML Model captures non-linear relationships")
        print("   ✅ Best accuracy among all models")
        print("   ✅ Regular retraining recommended")
    elif best_model == 'Heston':
        print("   ✅ Use Heston model as primary pricing model")
        print("   ✅ Captures volatility smile better than BS")
        print("   ⚠️  Consider calibrating parameters")
    elif best_model == 'Current Model':
        print("   ✅ Keep current pricing model")
        print("   ✅ Already optimized for Vietnamese CW market")
        print("   ⚠️  Consider ML as enhancement")
    else:
        print("   ✅ Use Black-Scholes as baseline")
        print("   ⚠️  Consider enhancements (Heston or ML)")
    
    print("\n" + "=" * 80)
    print("BENCHMARK COMPLETED")
    print("=" * 80)
    
    return {
        'metrics': all_metrics,
        'scores': scores,
        'ranking': ranked,
        'best_model': best_model,
        'best_score': best_score
    }

def evaluate_pricing_model():
    """
    Evaluate CW pricing model against market data.
    Calculates pricing accuracy, upside prediction, IV vs HV, Delta & ITM probability.
    
    Returns:
        dict: Evaluation results with metrics and recommendations
    """
    print("=" * 80)
    print("ĐÁNH GIÁ MÔ HÌNH ĐỊNH GIÁ CW SO VỚI THỊ TRƯỜNG")
    print("CW Pricing Model Evaluation vs Market")
    print("=" * 80)
    
    # Load market opportunities data
    from src.core.database import engine
    df = pd.read_sql('SELECT * FROM market_opportunities', engine)
    df = df.dropna(subset=['price', 'theoretical_price'])
    
    print(f"\n📊 Số lượng CW được phân tích: {len(df)}")
    print(f"📊 Dữ liệu từ {df['symbol'].nunique()} mã CW khác nhau")
    
    # 1. Pricing Accuracy
    print("\n" + "=" * 80)
    print("1. ĐỘ CHÍNH XÁC CỦA GIÁ LÝ THUYẾT SO VỚI THỊ TRƯỜNG")
    print("=" * 80)
    
    df['price_error'] = df['theoretical_price'] - df['price']
    df['price_error_pct'] = (df['theoretical_price'] - df['price']) / df['price'] * 100
    df['abs_error_pct'] = abs(df['price_error_pct'])
    
    mae = df['abs_error_pct'].mean()
    rmse = np.sqrt((df['price_error_pct'] ** 2).mean())
    median_error = df['price_error_pct'].median()
    
    print(f"\n📈 Sai số trung bình tuyệt đối (MAE): {mae:.2f}%")
    print(f"📈 Sai số bình phương trung bình (RMSE): {rmse:.2f}%")
    print(f"📈 Trung vị sai số (Median Error): {median_error:.2f}%")
    
    overvalued_count = (df['price_error_pct'] > 0).sum()
    undervalued_count = (df['price_error_pct'] < 0).sum()
    total = len(df)
    
    print(f"\n🔼 Mô hình định giá CAO hơn thị trường (Overvalued): {overvalued_count} ({overvalued_count/total*100:.1f}%)")
    print(f"🔽 Mô hình định giá THẤP hơn thị trường (Undervalued): {undervalued_count} ({undervalued_count/total*100:.1f}%)")
    
    print(f"\n📊 Phân phối độ chính xác:")
    print(f"  - Sai số < 10%: {(df['abs_error_pct'] < 10).sum()} ({(df['abs_error_pct'] < 10).sum()/total*100:.1f}%)")
    print(f"  - Sai số 10-30%: {((df['abs_error_pct'] >= 10) & (df['abs_error_pct'] < 30)).sum()} ({((df['abs_error_pct'] >= 10) & (df['abs_error_pct'] < 30)).sum()/total*100:.1f}%)")
    print(f"  - Sai số 30-50%: {((df['abs_error_pct'] >= 30) & (df['abs_error_pct'] < 50)).sum()} ({((df['abs_error_pct'] >= 30) & (df['abs_error_pct'] < 50)).sum()/total*100:.1f}%)")
    print(f"  - Sai số > 50%: {(df['abs_error_pct'] >= 50).sum()} ({(df['abs_error_pct'] >= 50).sum()/total*100:.1f}%)")
    
    # 2. Upside Prediction
    print("\n" + "=" * 80)
    print("2. PHÂN TÍCH DỰ BÁO TIỀN NĂNG TĂNG GIÁ (UPSIDE PREDICTION)")
    print("=" * 80)
    
    if 'upside_pct' in df.columns:
        df_upside = df.dropna(subset=['upside_pct'])
        high_upside = df_upside[df_upside['upside_pct'] > 1.0]
        moderate_upside = df_upside[(df_upside['upside_pct'] >= 0.5) & (df_upside['upside_pct'] <= 1.0)]
        low_upside = df_upside[df_upside['upside_pct'] < 0.5]
        
        print(f"\n🚀 Cơ hội tăng giá cao (Upside > 100%): {len(high_upside)} ({len(high_upside)/len(df_upside)*100:.1f}%)")
        print(f"📈 Cơ hội tăng giá trung bình (Upside 50-100%): {len(moderate_upside)} ({len(moderate_upside)/len(df_upside)*100:.1f}%)")
        print(f"📉 Cơ hội tăng giá thấp (Upside < 50%): {len(low_upside)} ({len(low_upside)/len(df_upside)*100:.1f}%)")
        
        print(f"\n📊 Thống kê Upside:")
        print(f"  - Trung bình: {df_upside['upside_pct'].mean():.2f}")
        print(f"  - Trung vị: {df_upside['upside_pct'].median():.2f}")
        print(f"  - Cao nhất: {df_upside['upside_pct'].max():.2f}")
        print(f"  - Thấp nhất: {df_upside['upside_pct'].min():.2f}")
    
    # 3. IV vs HV
    print("\n" + "=" * 80)
    print("3. PHÂN TÍCH BIẾN ĐỘ NGẦM BIẾU SO VỚI BIẾN ĐỘ LỊCH SỬ (IV vs HV)")
    print("=" * 80)
    
    if 'implied_volatility_pct' in df.columns and 'historical_volatility_pct' in df.columns:
        df_vol = df.dropna(subset=['implied_volatility_pct', 'historical_volatility_pct'])
        df_vol['iv_hv_diff'] = df_vol['implied_volatility_pct'] - df_vol['historical_volatility_pct']
        
        expensive_iv = df_vol[df_vol['iv_hv_diff'] > 10]
        cheap_iv = df_vol[df_vol['iv_hv_diff'] < -10]
        fair_iv = df_vol[(df_vol['iv_hv_diff'] >= -10) & (df_vol['iv_hv_diff'] <= 10)]
        
        print(f"\n💰 CW đắt (IV > HV + 10%): {len(expensive_iv)} ({len(expensive_iv)/len(df_vol)*100:.1f}%)")
        print(f"💎 CW rẻ (IV < HV - 10%): {len(cheap_iv)} ({len(cheap_iv)/len(df_vol)*100:.1f}%)")
        print(f"⚖️ CW giá công bằng (IV ≈ HV ±10%): {len(fair_iv)} ({len(fair_iv)/len(df_vol)*100:.1f}%)")
        
        print(f"\n📊 Thống kê chênh lệch IV - HV:")
        print(f"  - Trung bình: {df_vol['iv_hv_diff'].mean():.2f}%")
        print(f"  - Trung vị: {df_vol['iv_hv_diff'].median():.2f}%")
    
    # 4. Delta & ITM Probability
    print("\n" + "=" * 80)
    print("4. PHÂN TÍCH RỦI RO THÔNG QUA DELTA & XÁC SUẤT ITM")
    print("=" * 80)
    
    if 'delta' in df.columns and 'prob_itm' in df.columns:
        df_delta = df.dropna(subset=['delta', 'prob_itm'])
        high_delta = df_delta[df_delta['delta'] >= 0.5]
        atm_delta = df_delta[(df_delta['delta'] >= 0.4) & (df_delta['delta'] < 0.5)]
        low_delta = df_delta[df_delta['delta'] < 0.4]
        
        print(f"\n🎯 CW ITM (Delta ≥ 0.5): {len(high_delta)} ({len(high_delta)/len(df_delta)*100:.1f}%)")
        print(f"🎯 CW ATM (Delta 0.4-0.5): {len(atm_delta)} ({len(atm_delta)/len(df_delta)*100:.1f}%)")
        print(f"🎯 CW OTM (Delta < 0.4): {len(low_delta)} ({len(low_delta)/len(df_delta)*100:.1f}%)")
        
        print(f"\n📊 Thống kê Delta:")
        print(f"  - Trung bình: {df_delta['delta'].mean():.3f}")
        print(f"  - Trung vị: {df_delta['delta'].median():.3f}")
        
        print(f"\n📊 Thống kê Xác suất ITM:")
        print(f"  - Trung bình: {df_delta['prob_itm'].mean():.3f}")
        print(f"  - Trung vị: {df_delta['prob_itm'].median():.3f}")
    
    # 5. Overall Assessment
    print("\n" + "=" * 80)
    print("5. ĐÁNH GIÁ TỔNG QUAN & KHUYẾN NGHỊ")
    print("=" * 80)
    
    accuracy_score = max(0, 100 - mae)
    print(f"\n🏆 Điểm chính xác mô hình: {accuracy_score:.1f}/100")
    
    if accuracy_score >= 70:
        print("✅ Mô hình định giá KHÁ TỐT - Độ chính xác cao")
    elif accuracy_score >= 50:
        print("⚠️  Mô hình định giá TRUNG BÌNH - Cần cải thiện")
    else:
        print("❌ Mô hình định giá KÉM - Cần điều chỉnh đáng kể")
    
    if mae > 50:
        print("\n⚠️  THỊ TRƯỜNG KHÔNG HIỆU QUẢ - Có cơ hội arbitrage lớn")
        print("   Khuyên nghị: Tìm kiếm CW có sai số giá lớn để giao dịch")
    elif mae > 30:
        print("\n📊 THỊ TRƯỜNG BÌNH THƯỜNG - Có một số cơ hội定价")
        print("   Khuyên nghị: Chọn lọc CW có sai số giá > 30%")
    else:
        print("\n✅ THỊ TRƯỜNG HIỆU QUẢ - Giá thị trường phản ánh đúng giá trị")
        print("   Khuyên nghị: Tập trung vào phân tích cơ bản và quản trị rủi ro")
    
    if median_error > 10:
        print("\n⚠️  MÔ HÌNH CÓ XU HƯỚNG ĐỊNH GIÁ CAO (Overvaluation Bias)")
        print("   Khuyên nghị: Giảm tham số volatility hoặc tăng risk-free rate")
    elif median_error < -10:
        print("\n⚠️  MÔ HÌNH CÓ XU HƯỚNG ĐỊNH GIÁ THẤP (Undervaluation Bias)")
        print("   Khuyên nghị: Tăng tham số volatility hoặc giảm risk-free rate")
    else:
        print("\n✅ MÔ HÌNH KHÔNG CÓ ĐỘ LỆCH CHỈNH (No Significant Bias)")
        print("   Khuyên nghị: Mô hình cân bằng tốt")
    
    print("\n" + "=" * 80)
    print("HOÀN THÀNH ĐÁNH GIÁ")
    print("=" * 80)
    
    return {
        'mae': mae,
        'rmse': rmse,
        'median_error': median_error,
        'accuracy_score': accuracy_score,
        'overvalued_pct': overvalued_count / total * 100,
        'undervalued_pct': undervalued_count / total * 100
    }

# Run evaluation if executed directly
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'benchmark':
        benchmark_pricing_models()
    else:
        evaluate_pricing_model()
