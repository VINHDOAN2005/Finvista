# -*- coding: utf-8 -*-
"""
🏆 FINVISTA: COVERED WARRANT HISTORICAL ANALYSIS ENTRYPOINT
==========================================================
Usage:
  python run_cw_history.py --symbol CACB2510 --days 15

Author: samvo
"""
import sys
import os
import argparse

# Ensure project root is on PYTHONPATH when running as a script (python scripts/run_cw_history.py ...)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Force stdout encoding to UTF-8 to handle Vietnamese text beautifully on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from src.modules.cw_pricing.backtest.history_analyzer import analyze_historical_warrant

def main():
    parser = argparse.ArgumentParser(description="Finvista Covered Warrant Historical Volatility & Leverage Tracker")
    parser.add_argument('--symbol', '-s', type=str, required=True,
                        help="Covered Warrant symbol (e.g. CACB2510)")
    parser.add_argument('--days', '-d', type=int, default=15,
                        help="Number of trading days to analyze (default: 15)")
    args = parser.parse_args()
    
    symbol = args.symbol.upper().strip()
    days = args.days
    
    print(f"🏁 Launching historical quantitative analyzer for {symbol} over last {days} sessions...")
    analyze_historical_warrant(symbol, lookback_days=days)

if __name__ == "__main__":
    main()
