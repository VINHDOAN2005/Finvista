# -*- coding: utf-8 -*-
"""
🏆 FINVISTA: BATCH UNDERLYING STOCK (CPCS) HISTORICAL DATA EXTRACTOR
===================================================================
Fetches unique underlying stocks from the master covered warrant report,
downloads their historical quotes, and exports both individual and consolidated CSVs.
Supports multi-pass scanning and rate-limit cool-down periods.

Usage:
  python scripts/run_stock_history_all.py --days 180 --compile

Author: Antigravity
"""
import os
import sys
import argparse
import pandas as pd
from datetime import datetime, timedelta

# Ensure project root is on PYTHONPATH
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Force stdout encoding to UTF-8 to handle Vietnamese text beautifully on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Suppress vnstock warnings/banners
import contextlib
with contextlib.redirect_stdout(open(os.devnull, 'w')), \
     contextlib.redirect_stderr(open(os.devnull, 'w')):
    import vnstock

def main():
    parser = argparse.ArgumentParser(description="Fetch, sort and export historical prices for underlying stocks (CPCS)")
    parser.add_argument('--days', '-d', type=int, default=180,
                        help="Number of calendar days of stock history to fetch (default: 180)")
    parser.add_argument('--output-dir', '-o', type=str, default=os.path.join("data", "raw", "stock_history"),
                        help="Directory to save individual stock CSV files")
    parser.add_argument('--compile', '-c', action='store_true',
                        help="Compile all historical stock prices into a single master CSV file")
    parser.add_argument('--compile-file', type=str, default=os.path.join("data", "processed", "all_stock_historical_prices.csv"),
                        help="Path to save the master compiled CSV file")
    parser.add_argument('--force-download', '-f', action='store_true',
                        help="Force download even if the CSV file exists (ignores cache)")
    args = parser.parse_args()

    print("=" * 80)
    print(" 🚀 FINVISTA BATCH UNDERLYING STOCK HISTORY EXTRACTOR")
    print(f"  Looking back: {args.days} days | Output directory: {args.output_dir}")
    print("=" * 80)

    # 1. Fetch unique underlying stocks from our master report
    report_path = os.path.join("data", "processed", "excel_cw_report.csv")
    if not os.path.exists(report_path):
        print(f"❌ Master analysis report not found at {report_path}. Run python scripts/run_cw.py first!")
        return

    try:
        df = pd.read_csv(report_path)
        underlying_stocks = sorted(df['B_MaCPCS'].dropna().unique().tolist())
    except Exception as e:
        print(f"❌ Failed to parse master report: {e}")
        return

    if not underlying_stocks:
        print("❌ No underlying stocks found in the report.")
        return

    print(f"🎯 Found {len(underlying_stocks)} unique underlying stocks (CPCS).")

    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)

    # Date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=args.days)
    end_date_str = end_date.strftime('%Y-%m-%d')
    start_date_str = start_date.strftime('%Y-%m-%d')

    print(f"📡 Downloading historical quotes from {start_date_str} to {end_date_str}...\n")

    # Multi-pass setup
    pending_symbols = list(underlying_stocks)
    max_passes = 5
    pass_num = 1
    success_count = 0

    try:
        while pending_symbols and pass_num <= max_passes:
            if pass_num > 1:
                print(f"\n⚠️  [PASS {pass_num}/{max_passes}] Retrying for {len(pending_symbols)} failed/skipped stocks...")
                # Sleep for 15 seconds to let the rate limit window cool down
                cool_down = 15
                print(f"⏳ Cooling down for {cool_down} seconds to reset API rate limits...")
                import time
                time.sleep(cool_down)

            still_failed = []

            for i, symbol in enumerate(pending_symbols, 1):
                symbol = symbol.strip().upper()
                out_file = os.path.join(args.output_dir, f"{symbol}_history.csv")
                
                # Cache/Skip logic: Check if file already exists and is non-empty
                if not args.force_download and os.path.exists(out_file) and os.path.getsize(out_file) > 0:
                    success_count += 1
                    if pass_num == 1:
                        print(f"   [{i}/{len(pending_symbols)}] 💾 {symbol:<8} -> Loaded from local cache (skipped API)")
                    continue

                print(f"   [{i}/{len(pending_symbols)}] 📡 {symbol:<8} -> Fetching history...", end="", flush=True)

                max_retries = 3
                retry_delay = 5.0
                fetched_success = False

                for attempt in range(1, max_retries + 1):
                    try:
                        # Small throttle to avoid hitting API rate limits
                        import time
                        time.sleep(0.5)

                        quote = vnstock.Quote(symbol=symbol)
                        hist = quote.history(start=start_date_str, end=end_date_str)
                        
                        if hist.empty or 'close' not in hist.columns:
                            print(" ⚠️ Empty data. Saved empty file to cache.")
                            pd.DataFrame(columns=['symbol', 'date', 'open', 'high', 'low', 'close', 'volume']).to_csv(out_file, index=False)
                            fetched_success = True
                            break

                        # Standardize 'time' to 'date' if returned by newer vnstock versions
                        if 'time' in hist.columns and 'date' not in hist.columns:
                            hist = hist.rename(columns={'time': 'date'})

                        # Standardize date format
                        hist['date'] = pd.to_datetime(hist['date']).dt.strftime('%Y-%m-%d')
                        
                        # Sort individual stock history chronologically by date
                        hist = hist.sort_values('date').reset_index(drop=True)

                        # Convert prices to VND (vnstock returns thousands of VND)
                        price_cols = ['open', 'high', 'low', 'close', 'ref_price']
                        for col in price_cols:
                            if col in hist.columns:
                                hist[col] = hist[col] * 1000

                        # Insert identifier column
                        hist.insert(0, 'symbol', symbol)

                        # Save individual file
                        hist.to_csv(out_file, index=False)
                        
                        success_count += 1
                        print(f" ✅ Saved {len(hist)} sessions to CSV")
                        fetched_success = True
                        break

                    except (Exception, SystemExit) as e:
                        # Handle rate limit and other issues by sleeping and retrying
                        if attempt < max_retries:
                            import time
                            time.sleep(retry_delay)
                            retry_delay *= 2
                        else:
                            pass

                if not fetched_success:
                    print(" ❌ Failed (rate limit / network error). Will retry in next pass.")
                    still_failed.append(symbol)

            pending_symbols = still_failed
            pass_num += 1

    except KeyboardInterrupt:
        print("\n🛑 Download interrupted by user. Compiling successfully downloaded data so far...")
    except BaseException as e:
        print(f"\n⚠️ Unexpected crash or library shutdown: {e}. Compiling available data...")

    finally:
        print("-" * 80)
        # 2. Compile into a single CSV if requested
        if args.compile:
            print(f"🗂️ Compiling all available historical stock data from {args.output_dir}...")
            all_stocks_data = []
            
            # Read all generated CSV files from disk
            for symbol in underlying_stocks:
                out_file = os.path.join(args.output_dir, f"{symbol}_history.csv")
                if os.path.exists(out_file) and os.path.getsize(out_file) > 0:
                    try:
                        df_stock = pd.read_csv(out_file)
                        if not df_stock.empty:
                            all_stocks_data.append(df_stock)
                    except Exception as e:
                        print(f"⚠️  Could not read cached file for {symbol}: {e}")

            if all_stocks_data:
                compiled_df = pd.concat(all_stocks_data, ignore_index=True)
                
                # Sort compiled DataFrame by symbol (alphabetically) and then date (chronologically)
                compiled_df = compiled_df.sort_values(by=['symbol', 'date']).reset_index(drop=True)
                
                compiled_df.to_csv(args.compile_file, index=False)
                print(f"💾 Consolidated historical dataset successfully saved to: {args.compile_file}")
                print(f"   Total rows compiled: {len(compiled_df):,}")
                print(f"🎉 Process completed successfully!")
            else:
                print("⚠️  No historical price data available to compile.")
        print("=" * 80)

if __name__ == '__main__':
    main()
