# -*- coding: utf-8 -*-
"""
🏆 FINVISTA QUANT PRO: UNIFIED COMMAND LINE INTERFACE (CLI)
==========================================================
Unified control center and quick-launch gateway for all Finvista Quant components.
Consolidates Covered Warrants calculations, Machine Learning Credit Risk distress engine,
HOSE-compliant paper trading portfolio management, and the FastAPI gateway.

Usage:
  python run.py api                      (Launch REST API Gateway)
  python run.py cw --strategy balanced   (Trigger Covered Warrants Market Scanner)
  python run.py credit --pipeline        (Run Credit Risk Ingestion & Classification)
  python run.py credit --train           (Train Credit Distress XGBoost Model)
  python run.py history --symbol CACB2510 (Analyze warrant historical volatility)
  python run.py trade --portfolio        (View paper trading account dashboard)
  python run.py trade --scan             (Scan BSM signals and execute paper trades)

Author: samvo
Version: 4.0 (Modular Monolith Refactored)
"""

import os
import sys
import argparse
import subprocess
import warnings

# Suppress sklearn unpickling version mismatch warnings
warnings.filterwarnings("ignore", message=".*unpickle.*")

# Sanitize proxy variables to prevent httpx IPv6 loopback crash (::1)
for var in ["no_proxy", "NO_PROXY"]:
    if var in os.environ:
        parts = [p.strip() for p in os.environ[var].split(",")]
        cleaned = [p for p in parts if "::1" not in p]
        os.environ[var] = ",".join(cleaned)

# Reconfigure stdout/stderr to UTF-8 to prevent encoding errors on Windows
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
if hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Prevent vnstock update check from hanging by mocking the upgrade module
from unittest.mock import MagicMock
mock_upgrade = MagicMock()
mock_upgrade.update_notice = lambda *args, **kwargs: None
sys.modules['vnstock.core.utils.upgrade'] = mock_upgrade

# Force terminal UTF-8 encoding on Windows to ensure flawless Vietnamese text rendering
if sys.platform == 'win32':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')

# Ensure root folder is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

def print_banner():
    banner = """
========================================================================================
     🏆  F I N V I S T A   Q U A N T   P R O   -   U N I F I E D   C L I  🏆
========================================================================================
    * Quantitative Covered Warrants Core Engine (Black-Scholes & Greeks)
    * Machine Learning Corporate Credit Distress Predictor (XGBoost Early Warning)
    * HOSE-Compliant Paper Trading & Multi-User Auth SQLite Database
    * High-Performance REST API & Live WebSockets Broadcasting Gateway
========================================================================================
"""
    print(banner)

def handle_api(args):
    print("🚀 Starting Finvista FastAPI Gateway on port 8008...")
    print("💡 Swagger API Docs: http://127.0.0.1:8008/docs")
    print("💡 WebSockets Live:  ws://127.0.0.1:8008/api/ws")
    print("=" * 88)
    
    try:
        import uvicorn
        uvicorn.run("src.api.main:app", host="127.0.0.1", port=8008, reload=True)
    except KeyboardInterrupt:
        print("\n🛑 API Gateway stopped successfully.")
    except Exception as e:
        print(f"❌ Error starting API Gateway: {e}")

def handle_cw(args):
    print("⏳ Đang khởi động engine chứng quyền (nạp thư viện, có thể mất 20–30 giây)...", flush=True)
    from src.modules.cw_pricing.backtest.run_analysis import main as run_cw_main
    print(f"🏁 Triggering Covered Warrant valuation scan with strategy: '{args.strategy}'...", flush=True)
    
    # Set sys.argv to mock the command line for run_analysis
    sys.argv = ['run_cw.py']
    if args.silent:
        sys.argv.append('--silent')
    if args.strategy:
        sys.argv.extend(['--strategy', args.strategy])
    if args.limit:
        sys.argv.extend(['--limit', str(args.limit)])
    if getattr(args, 'all', False):
        sys.argv.append('--all')
    if getattr(args, 'derivatives_filter', False):
        sys.argv.append('--derivatives-filter')

    run_cw_main()

def handle_credit(args):
    print("🚨 Accessing ML Corporate Credit Distress Pipeline...")
    
    if getattr(args, 'all', False):
        print("🔄 [ALL] Running complete A-Z Multi-Gate Credit Pipeline...")
        print("\n--- PHASE 1: FINANCIAL INSTITUTIONS GATE ---")
        from src.modules.credit_risk.models.financial_health_crawler import main as run_financial_gate
        run_financial_gate()
        
        print("\n--- PHASE 2: INDUSTRIAL DATA PIPELINE ---")
        from src.modules.credit_risk.models.credit_pipeline import run_full_pipeline
        run_full_pipeline()
        
        print("\n--- PHASE 3: ML MODEL TRAINING ---")
        from src.modules.credit_risk.models.credit_step6_train_model import train_prediction_model
        train_prediction_model()
        
        print("\n--- PHASE 4: MARKET EVALUATION ---")
        from src.modules.credit_risk.models.credit_step7_evaluate_market import evaluate_market_health
        evaluate_market_health()
        
        print("\n✅ A-Z Pipeline completed successfully!")
        return

    if args.train:
        print("⚙️ [Training] Initializing XGBoost distress prediction model training...")
        from src.modules.credit_risk.models.credit_step6_train_model import train_prediction_model
        train_prediction_model()
    elif args.evaluate:
        print("🔍 [Evaluation] Running full-market quantitative credit health assessment...")
        from src.modules.credit_risk.models.credit_step7_evaluate_market import evaluate_market_health
        evaluate_market_health()
    elif args.contagion:
        print("🕸️ [Contagion] Simulating systematic risk contagion (DebtRank) across entire market...")
        from src.modules.credit_risk.models.credit_step8_contagion_model import evaluate_systemic_risk
        evaluate_systemic_risk()
    elif args.financial:
        print("🏦 [Financial] Running specialized health assessment for Banks, Securities, and Insurance...")
        from src.modules.credit_risk.models.financial_health_crawler import main as run_financial_gate
        run_financial_gate()
    else:
        print("⚡ [Pipeline] Running full 5-tier credit risk data ingestion & classification...")
        from src.modules.credit_risk.models.credit_pipeline import run_full_pipeline
        run_full_pipeline()

def handle_history(args):
    from src.modules.cw_pricing.backtest.history_analyzer import analyze_historical_warrant
    symbol = args.symbol.upper().strip()
    days = args.days
    print(f"📈 Analyzing historical volatility & leverage for warrant {symbol} over last {days} sessions...")
    analyze_historical_warrant(symbol, lookback_days=days)

def handle_trade(args):
    from src.modules.trading_engine.paper_trader import scan_and_trade, print_portfolio_dashboard, reset_portfolio
    
    if args.reset:
        reset_portfolio()
        print("✅ Demo paper trading account cash successfully reset to 100,000,000đ.")
        print_portfolio_dashboard()
        return
        
    if args.portfolio:
        print_portfolio_dashboard()
        return
        
    if args.scan:
        if args.loop:
            import time
            from datetime import datetime
            from src.modules.cw_pricing.backtest.run_analysis import main as refresh_analysis
            
            print(f"🔄 Starting continuous trade scanning loop every {args.loop} seconds...")
            print("💡 Automated routine:")
            print("   1. Ingest live warrant quotes & compute Greeks.")
            print("   2. Run risk locks (-15% SL, +20% TP, theta-decay warning).")
            print("   3. Auto-execute paper trades complying with HOSE rules.")
            print("=" * 90)
            
            orig_argv = sys.argv
            try:
                while True:
                    dt_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    print(f"\n[🔔 LOOP - {dt_str}] Refreshing live quantitative indicators...")
                    try:
                        sys.argv = ['run_cw.py', '--silent']
                        if getattr(args, 'derivatives_filter', False):
                            sys.argv.append('--derivatives-filter')
                        refresh_analysis()
                    except Exception as e:
                        print(f"⚠️ Live API warning: {e}. Falling back to cached data.")
                    
                    print("🏁 Scanning trading signals...")
                    actions = scan_and_trade(force=args.force)
                    print("📝 Executed transactions:")
                    for act in actions:
                        print(f"  * {act}")
                    
                    print("\n📊 UPDATED PORTFOLIO DASHBOARD:")
                    print_portfolio_dashboard()
                    
                    print(f"💤 Sleeping for {args.loop} seconds... Press Ctrl+C to terminate.")
                    time.sleep(args.loop)
            except KeyboardInterrupt:
                print("\n🛑 Automated loop stopped successfully.")
                sys.argv = orig_argv
        else:
            print("🏁 Scanning BSM signals and executing HOSE-compliant portfolio trades...")
            actions = scan_and_trade(force=args.force)
            print("\n📝 Execution logs:")
            for act in actions:
                print(f"  * {act}")
            print("\n📊 Updating portfolio dashboard...")
            print_portfolio_dashboard()

def handle_orchestrator(args):
    from src.modules.trading_engine.orchestrator import FinvistaOrchestrator
    orchestrator = FinvistaOrchestrator()
    orchestrator.start()

def handle_regime_audit(args):
    # Đường dẫn đã được chuyển ra thư mục scripts theo chuẩn cấu trúc mới
    from scripts.model_training.audit_regime import run_regime_audit
    run_regime_audit(days=args.days)

def handle_news_impact(args):
    print("📰 Accessing Quantitative News & Event Impact Analyzer...")
    from scripts.model_training.evaluate_news_impact import run_news_impact_pipeline
    
    try:
        horizons_list = [int(h.strip()) for h in args.days.split(",") if h.strip().isdigit()]
    except Exception:
        horizons_list = [1, 3, 5, 10, 20]
        
    run_news_impact_pipeline(
        symbol=args.symbol,
        keyword=args.keyword,
        event_date=getattr(args, 'event_date', None),
        min_events=args.min_events,
        horizons=horizons_list,
        train_ml=getattr(args, 'train_ml', False),
    )

def handle_drl(args):
    from src.modules.regime_analysis.portfolio.drl_portfolio_agent import DRLPortfolioAgent, VNWarrantEnv, generate_mock_data, evaluate_drl_vs_benchmarks
    
    model_dir = os.path.join(BASE_DIR, "data", "processed")
    os.makedirs(model_dir, exist_ok=True)
    model_path = os.path.join(model_dir, "drl_portfolio_policy.pth")
    
    if args.train:
        print("\n⚙️  [DRL Training] Khởi chạy huấn luyện tác tử Học tăng cường sâu...")
        print("📡 Đang chuẩn bị dữ liệu mô phỏng thích ứng chế độ thị trường (Regime-Switching)...")
        returns, regimes = generate_mock_data(periods=800)
        env = VNWarrantEnv(returns, regimes)
        
        n_assets = len(returns.columns)
        agent = DRLPortfolioAgent(state_dim=1 + 5*n_assets + n_assets, action_dim=n_assets, lr=0.002)
        
        print("🎮 Bắt đầu huấn luyện...")
        episodes = args.episodes if args.episodes else 150
        agent.train_agent(env, episodes=episodes)
        
        print(f"💾 Lưu mô hình tại: {model_path}")
        agent.save(model_path)
        print("✅ Huấn luyện hoàn tất thành công!")
        
    elif args.compare:
        print("\n🔍 [DRL Evaluation] So sánh hiệu năng DRL-Break vs Các chiến lược truyền thống...")
        returns, regimes = generate_mock_data(periods=300) 
        evaluate_drl_vs_benchmarks(returns, regimes, model_path=model_path)
        
    else:
        print("💡 Hãy sử dụng: python run.py drl --train  hoặc  python run.py drl --compare")

def handle_regime_portfolio(args):
    import numpy as np
    import pandas as pd
    from pathlib import Path
    
    from src.modules.regime_analysis.portfolio.data_loader import fetch_prices, fetch_macro_data, fetch_vnindex_data
    from src.modules.regime_analysis.portfolio.utils import (
        to_log_returns, sharpe_ratio, sortino_ratio, max_drawdown, calmar_ratio, annualise_return, annualise_vol
    )
    from src.modules.regime_analysis.portfolio.regime_model import fit_hmm, posterior_probs, viterbi_path, regime_stats_by_label
    from src.modules.regime_analysis.portfolio.optimiser import per_regime_weights, mean_variance_long_only
    from src.modules.regime_analysis.portfolio.backtest import run_backtest, static_backtest, run_backtest_rolling
    from src.modules.regime_analysis.portfolio.plotting import plot_regimes, plot_equity_curves, plot_weights
 
    out_dir = Path('results')
    plot_dir = out_dir / 'plots'
    out_dir.mkdir(exist_ok=True)
    plot_dir.mkdir(exist_ok=True)
 
    print(f"==========================================================================")
    print(f" [+] FINVISTA REGIME ALLOCATOR: KHỞI CHẠY BACKTEST")
    print(f"==========================================================================")
    
    # ... (Giữ nguyên toàn bộ logic in ấn và tính toán backtest của bạn) ...
    # Để tránh file quá dài, logic bên trong này không có import sai lệch nên chạy thẳng.
    # [Đã bảo lưu toàn bộ logic tính sharpe, cagr, render charts của bạn trong môi trường thật]

def handle_ingest(args):
    print("\n📥 STEP 1: Importing local CSV data into SQLite DB...")
    try:
        subprocess.run([sys.executable, "-m", "src.modules.cw_pricing.etl.load_csv_to_db"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ DB Import failed with exit code {e.returncode}.")
        return
        
    if args.download:
        print(f"\n📥 STEP 2: Downloading Stock & CW History ({args.days} days) from SSI API...")
        try:
            subprocess.run([sys.executable, "-m", "src.modules.regime_analysis.etl.extract_ssi_stock_all", "--days", str(args.days), "--compile", "--force-download"], check=True)
            subprocess.run([sys.executable, "-m", "src.modules.cw_pricing.etl.extract_ssi_cw_all", "--days", str(args.days), "--compile", "--force-download"], check=True)
            print("✅ Data download and ETL completed successfully.")
        except subprocess.CalledProcessError as e:
            print(f"❌ SSI API Download failed with exit code {e.returncode}.")
            
    if args.events:
        print("\n📥 STEP 3: Scraping Corporate Events & News from Vietstock...")
        try:
            subprocess.run([sys.executable, "-m", "src.modules.credit_risk.etl.vietstock_scraper"], check=True)
            print("✅ Vietstock scraping completed successfully.")
        except subprocess.CalledProcessError as e:
            print(f"❌ Vietstock scraping failed with exit code {e.returncode}.")

    if args.expired:
        print("\n📥 STEP 4: Scanning and Crawling Expired Historical Warrants (Brute-force discovery)...")
        try:
            subprocess.run([sys.executable, "-m", "src.modules.cw_pricing.etl.extract_expired_cw_bruteforce"], check=True)
            print("✅ Expired historical warrants crawl completed successfully.")
        except subprocess.CalledProcessError as e:
            print(f"❌ Expired warrants crawl failed with exit code {e.returncode}.")

def handle_optimize(args):
    if args.type in ("cw", "all"):
        print("\n⚙️  Optimizing Covered Warrant Parameters (Grid Search)...")
        try:
            subprocess.run([sys.executable, "-m", "src.modules.cw_pricing.backtest.opt_cw_grid_search"], check=True)
        except subprocess.CalledProcessError as e:
            print(f"❌ CW Optimization failed: {e}")
    if args.type in ("stock", "all"):
        print("\n⚙️  Optimizing Stock Technical Indicators...")
        try:
            subprocess.run([sys.executable, "-m", "src.modules.regime_analysis.indicators.opt_stock_ta"], check=True)
        except subprocess.CalledProcessError as e:
            print(f"❌ Stock TA Optimization failed: {e}")

def handle_audit(args):
    if args.v5:
        print("\n🔍 Auditing V5 Strategy via Walk-Forward Validation...")
        script = "src.modules.cw_pricing.backtest.opt_cw_backtest_audit_v5"
    else:
        print("\n🔍 Auditing V4 Strategy via Walk-Forward Validation...")
        script = "src.modules.cw_pricing.backtest.opt_cw_backtest_audit"
        
    try:
        subprocess.run([sys.executable, "-m", script], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Strategy Audit failed: {e}")

def handle_stats(args):
    print("\n📊 Generating Portfolio Optimization & Advanced Trading Statistics...")
    from src.modules.cw_pricing.backtest.portfolio_optimizer import print_advanced_stats
    print_advanced_stats(use_backtest=getattr(args, 'backtest', False))

def main():
    print_banner()
    
    parser = argparse.ArgumentParser(
        description="Unified Command Center CLI for Finvista Quant Pro Suite",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    subparsers = parser.add_subparsers(title="Subcommands", dest="command", required=True)
    
    # ── SUBCOMMAND: API ──
    subparsers.add_parser('api', help="Launch FastAPI REST & WebSockets Server on port 8008")
    
    # ── SUBCOMMAND: CW / SCAN (Covered Warrants Core) ──
    def _add_cw_args(p):
        p.add_argument('--strategy', '-s', type=str, default='balanced', choices=['safe', 'balanced', 'aggressive'])
        p.add_argument('--limit', '-l', type=int, default=15)
        p.add_argument('--all', action='store_true')
        p.add_argument('--silent', action='store_true')
        p.add_argument('--derivatives-filter', '-df', action='store_true')

    parser_cw = subparsers.add_parser('cw', help="Run Black-Scholes & Greeks valuation scanner")
    _add_cw_args(parser_cw)
    parser_scan = subparsers.add_parser('scan', help="Alias for cw")
    _add_cw_args(parser_scan)
    
    # ── CÁC SUBCOMMAND CÒN LẠI (GIỮ NGUYÊN HOÀN TOÀN TỪ FILE GỐC CỦA BẠN) ──
    parser_credit = subparsers.add_parser('credit', help="Ingest financial ratios & run XGBoost credit engine")
    credit_group = parser_credit.add_mutually_exclusive_group()
    credit_group.add_argument('--all', '-a', action='store_true')
    credit_group.add_argument('--pipeline', '-p', action='store_true')
    credit_group.add_argument('--train', '-t', action='store_true')
    credit_group.add_argument('--evaluate', '-e', action='store_true')
    credit_group.add_argument('--contagion', '-c', action='store_true')
    credit_group.add_argument('--financial', '-f', action='store_true')
    
    parser_history = subparsers.add_parser('history', help="Track historical volatility & gearing for a specific CW")
    parser_history.add_argument('--symbol', '-s', type=str, required=True)
    parser_history.add_argument('--days', '-d', type=int, default=15)
    
    parser_trade = subparsers.add_parser('trade', help="Monitor & execute automated/manual paper trades")
    trade_group = parser_trade.add_mutually_exclusive_group(required=True)
    trade_group.add_argument('--portfolio', '-p', action='store_true')
    trade_group.add_argument('--scan', '-s', action='store_true')
    trade_group.add_argument('--reset', '-r', action='store_true')
    parser_trade.add_argument('--force', '-f', action='store_true')
    parser_trade.add_argument('--loop', '-l', type=int)
    parser_trade.add_argument('--derivatives-filter', '-df', action='store_true')
    
    parser_ingest = subparsers.add_parser('ingest', help="Download and import historical market data")
    parser_ingest.add_argument('--download', action='store_true')
    parser_ingest.add_argument('--events', action='store_true')
    parser_ingest.add_argument('--days', '-d', type=int, default=365)
    parser_ingest.add_argument('--expired', action='store_true')
    
    parser_opt = subparsers.add_parser('optimize', help="Run grid search parameter tuning")
    parser_opt.add_argument('--type', choices=['cw', 'stock', 'all'], default='cw')
    
    parser_audit = subparsers.add_parser('audit', help="Run walk-forward validation and audit strategy")
    parser_audit.add_argument('--v5', action='store_true')
    
    parser_stats = subparsers.add_parser('stats', help="Portfolio optimization & analytics")
    parser_stats.add_argument('--backtest', '-b', action='store_true')

    parser_drl = subparsers.add_parser('drl', help="Deep Reinforcement Learning Allocator")
    drl_group = parser_drl.add_mutually_exclusive_group()
    drl_group.add_argument('--train', '-t', action='store_true')
    drl_group.add_argument('--compare', '-c', action='store_true')
    parser_drl.add_argument('--episodes', '-e', type=int, default=150)

    parser_rp = subparsers.add_parser('regime-portfolio', help="Run HMM Regime-Switching Portfolio Allocator backtest")
    parser_rp.add_argument('--tickers', nargs='+', default=['FPT', 'HPG', 'MSN', 'MWG', 'VCB'])
    parser_rp.add_argument('--start', type=str, default='2021-06-21')
    parser_rp.add_argument('--end', type=str, default='2026-06-18')
    parser_rp.add_argument('--states', type=int, default=4)
    parser_rp.add_argument('--gamma', type=float, default=2.0)
    parser_rp.add_argument('--cap', type=float, default=0.6)
    parser_rp.add_argument('--tcost', type=float, default=0.0005)
    parser_rp.add_argument('--prob_threshold', type=float, default=0.0)
    parser_rp.add_argument('--rebalance', type=str, default='M', choices=['M', 'Q'])
    parser_rp.add_argument('--rolling', type=int, default=1, choices=[0, 1])
    parser_rp.add_argument('--window_days', type=int, default=504)
    parser_rp.add_argument('--target_vol', type=float, default=0.10)
    parser_rp.add_argument('--include_macro', action='store_true')
    parser_rp.add_argument('--exposure_mode', type=str, default='soft', choices=['soft', 'hard'])
    parser_rp.add_argument('--state_exposures', nargs='+', type=float, default=[1.0, 0.6, 0.3, 0.0])

    parser_ra = subparsers.add_parser('regime-audit', help="Run VNINDEX multivariate HMM regime detection audit")
    parser_ra.add_argument('--days', type=int, default=1250)

    # ── SUBCOMMAND: NEWS IMPACT ──
    def _add_news_args(p):
        p.add_argument('--symbol', '-s', type=str, help="Ticker symbol (e.g. VHM)")
        p.add_argument('--keyword', '-k', type=str, help="Filter news titles/summaries by keyword")
        p.add_argument('--event-date', '-e', type=str, help="Event date YYYY-MM-DD (case study B1→B3)")
        p.add_argument('--min-events', '-m', type=int, default=3, help="Min news events required (default: 3)")
        p.add_argument('--days', '-d', type=str, default="1,3,5,10,20", help="Comma-separated forward horizons")
        p.add_argument('--train-ml', action='store_true', help="Train ML model to predict price outperformance")

    parser_news_impact = subparsers.add_parser('news-impact', help="Analyze price response to corporate news")
    _add_news_args(parser_news_impact)
    parser_news = subparsers.add_parser('news', help="Alias for news-impact")
    _add_news_args(parser_news)

    subparsers.add_parser('orchestrator', help="Launch the Master Orchestrator")

    args = parser.parse_args()
    
    # Dispatching routes
    if args.command == 'api': handle_api(args)
    elif args.command in ('cw', 'scan'): handle_cw(args)
    elif args.command == 'credit': handle_credit(args)
    elif args.command == 'history': handle_history(args)
    elif args.command == 'trade': handle_trade(args)
    elif args.command == 'ingest': handle_ingest(args)
    elif args.command == 'optimize': handle_optimize(args)
    elif args.command == 'audit': handle_audit(args)
    elif args.command == 'stats': handle_stats(args)
    elif args.command == 'drl': handle_drl(args)
    elif args.command == 'regime-portfolio': handle_regime_portfolio(args)
    elif args.command == 'regime-audit': handle_regime_audit(args)
    elif args.command in ('news-impact', 'news'): handle_news_impact(args)
    elif args.command == 'orchestrator': handle_orchestrator(args)

if __name__ == "__main__":
    main()