# -*- coding: utf-8 -*-
"""
🏆 FINVISTA: HISTORICAL EXPIRED COVERED WARRANT CRAWLER (BRUTE-FORCE SEARCH)
===========================================================================
Crawls and downloads historical price series for expired covered warrants (CWs) 
in the past. Since expired CWs are removed from active broker lists, this script 
uses a smart brute-force search over naming conventions to discover and extract them.

Pattern: C + <UNDERLYING> + <YEAR> + <SEQUENCE>
Example: CHPG2301, CFPT2405

Features:
  - Cache checking (skips already downloaded files).
  - Negative caching (writes empty placeholder for invalid tickers to avoid querying again).
  - Polite rate limiting (small sleep delays).
  - Standardizes column names and prices to VND.

Author: Antigravity
"""
import os
import sys
import argparse
import pandas as pd
from datetime import datetime
import time

# Ensure project root is on PYTHONPATH
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Force terminal UTF-8 encoding on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Suppress vnstock banners/warnings for a cleaner CLI experience
import contextlib
import io

def mock_upgrade_notice(*args, **kwargs):
    pass

with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    from unittest.mock import MagicMock
    mock_upgrade = MagicMock()
    mock_upgrade.update_notice = mock_upgrade_notice
    sys.modules['vnstock.core.utils.upgrade'] = mock_upgrade
    # Also try to mock the insiders banner which is common in 4.x
    mock_insiders = MagicMock()
    mock_insiders.insiders_notice = mock_upgrade_notice
    sys.modules['vnstock.core.utils.insiders'] = mock_insiders
    import vnstock

# Target stock list matching HOSE VN30 CW underlyings and common mid-caps
DEFAULT_UNDERLYINGS = [
    'ACB', 'BCM', 'BID', 'BVH', 'CTG', 'FPT', 'GAS', 'GVR', 'HDB', 'HPG', 
    'MBB', 'MSN', 'MWG', 'PLX', 'POW', 'REE', 'SAB', 'SHB', 'SSB', 'SSI', 
    'STB', 'TCB', 'TPB', 'VCB', 'VHM', 'VIB', 'VIC', 'VNM', 'VPB', 'VRE',
    'PNJ', 'GMD', 'KDH', 'DGC', 'NVL', 'PDR'
]

def generate_candidate_symbols(underlyings, years, max_sequence):
    """Generate all standard CW candidate tickers for brute-forcing."""
    candidates = []
    for u in sorted(underlyings):
        for y in years:
            for seq in range(1, max_sequence + 1):
                symbol = f"C{u}{y:02d}{seq:02d}"
                candidates.append((symbol, u, y))
    return candidates

def main():
    parser = argparse.ArgumentParser(description="Brute-force and fetch history for expired/historical covered warrants.")
    parser.add_argument('--underlyings', '-u', nargs='+', default=DEFAULT_UNDERLYINGS,
                        help="List of underlying stock symbols (default: VN30 basket + mid-caps)")
    parser.add_argument('--years', '-y', type=int, nargs='+', default=[21, 22, 23, 24, 25, 26],
                        help="Two-digit years to search (default: 21-26)")
    parser.add_argument('--max-seq', '-s', type=int, default=60,
                        help="Maximum sequence number per year (default: 60)")
    parser.add_argument('--output-dir', '-o', type=str, default=os.path.join("data", "raw", "cw_history"),
                        help="Directory to save individual warrant CSV files")
    parser.add_argument('--force-download', '-f', action='store_true',
                        help="Force download even if the CSV file exists")
    args = parser.parse_args()

    print("=" * 80)
    print(" 🚀 FINVISTA EXPIRED COVERED WARRANT BRUTE-FORCE CRAWLER")
    print(f"  Underlying basket: {len(args.underlyings)} stocks")
    print(f"  Years: {args.years}")
    print(f"  Max sequence per year: {args.max_seq}")
    print(f"  Output directory: {args.output_dir}")
    print("=" * 80)

    os.makedirs(args.output_dir, exist_ok=True)
    candidates = generate_candidate_symbols(args.underlyings, args.years, args.max_seq)
    print(f"🎯 Generated {len(candidates)} candidate tickers to scan.")

    # Exclude currently active ones if we want, or let caching handle it
    scanned_count = 0
    found_count = 0
    error_consecutive = 0

    for idx, (symbol, underlying, year) in enumerate(candidates, 1):
        out_file = os.path.join(args.output_dir, f"{symbol}_history.csv")
        
        # 1. Caching logic: check if already exists
        if not args.force_download and os.path.exists(out_file):
            # If it exists, skip
            if os.path.getsize(out_file) > 100: # Found warrant
                found_count += 1
            continue

        print(f"   [{idx}/{len(candidates)}] 📡 Testing {symbol:<8}...", end="", flush=True)
        scanned_count += 1
        
        # 2. Query historical data for that year
        start_date = f"20{year}-01-01"
        # Covered warrants can last up to 12 months, let's query up to mid of next year
        end_date = f"20{year+1}-07-01"
        
        # Throttling
        time.sleep(1.0)
        
        try:
            # Re-suppress for every call because vnstock might print on domain instantiation
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                quote = vnstock.Quote(symbol=symbol)
                hist = quote.history(start=start_date, end=end_date)
            
            error_consecutive = 0
            
            if hist is None or hist.empty or 'close' not in hist.columns:
                print(" ❌ Not Found (negative cached).")
                # Save empty placeholder CSV to avoid querying again
                pd.DataFrame(columns=['symbol', 'date', 'open', 'high', 'low', 'close', 'volume']).to_csv(out_file, index=False)
                continue
            
            # Standardize date column
            if 'time' in hist.columns and 'date' not in hist.columns:
                hist = hist.rename(columns={'time': 'date'})
                
            hist['date'] = pd.to_datetime(hist['date']).dt.strftime('%Y-%m-%d')
            hist = hist.sort_values('date').reset_index(drop=True)

            # Convert prices to VND
            price_cols = ['open', 'high', 'low', 'close', 'ref_price']
            for col in price_cols:
                if col in hist.columns:
                    hist[col] = hist[col] * 1000

            hist.insert(0, 'symbol', symbol)
            hist.to_csv(out_file, index=False)
            
            found_count += 1
            print(f" 🎉 Found! Saved {len(hist)} trading sessions.")
            time.sleep(2.0)
            
        except (SystemExit, KeyboardInterrupt) as e:
            if isinstance(e, KeyboardInterrupt):
                print("\n🛑 Interrupted by user.")
                break
            print(" ⏳ Rate limit hit (SystemExit). Cooling down for 70s...")
            error_consecutive += 1
            time.sleep(70)

        except BaseException as e:
            error_msg = str(e).lower()
            error_consecutive += 1

            is_not_found = (
                "retryerror" in error_msg and "valueerror" in error_msg
            ) or "no data" in error_msg or "symbol not found" in error_msg

            is_rate_limit = (
                "too many requests" in error_msg
                or "rate limit" in error_msg
                or "429" in error_msg
            )

            if is_not_found:
                print(" ❌ Not Found (negative cached).")
                pd.DataFrame(columns=['symbol', 'date', 'open', 'high', 'low', 'close', 'volume']).to_csv(out_file, index=False)
                error_consecutive = 0
            elif is_rate_limit:
                print(f" ⚠️ Rate limit warning. Cooling down for 70s...")
                time.sleep(70)
                error_consecutive = 0
            else:
                print(f" ⚠️ Error: {e}")

            if error_consecutive >= 15:
                print("❌ Too many consecutive API errors. Aborting to avoid IP ban.")
                break

    print("=" * 80)
    print(f"🏁 Scanned {scanned_count} candidates.")
    print(f"📊 Total valid expired CWs stored in database/cache: {found_count}")
    print("=" * 80)

if __name__ == '__main__':
    main()
