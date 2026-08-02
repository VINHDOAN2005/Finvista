"""
Import ALL CW history CSV files into the database for comprehensive backtesting.
Also imports corresponding stock history for each underlying stock.
"""
import os
import sys
import pandas as pd
import warnings

warnings.filterwarnings('ignore')

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.core.database import engine
import contextlib

# Suppress vnstock banners
with contextlib.redirect_stdout(open(os.devnull, 'w')), \
     contextlib.redirect_stderr(open(os.devnull, 'w')):
    import vnstock

CW_DIR = os.path.join(PROJECT_ROOT, "data", "raw", "cw_history")

def extract_stock_symbol(cw_symbol):
    """Extract underlying stock symbol from CW symbol. E.g. CACB2510 -> ACB, CFPT2517 -> FPT"""
    # CW format: C<STOCK><YYMM> e.g. CACB2510, CFPT2517, CHPG2523
    s = cw_symbol[1:]  # Remove leading 'C'
    # Try known stock symbols from longest to shortest
    known_stocks = [
        'VNM', 'VPB', 'VRE', 'VIC', 'VIB', 'VJC', 'VHM',
        'TCB', 'TPB', 'STB', 'SSB', 'SHB',
        'MSN', 'MWG', 'MBB', 'LPB',
        'HPG', 'HDB', 'FPT', 'DGC', 'ACB',
        'BCM', 'BID', 'BVH', 'CTG', 'GAS', 'GVR', 'PLX',
        'POW', 'REE', 'SAB', 'SSI', 'VCB', 'PNJ', 'GMD',
        'KDH', 'NVL', 'PDR'
    ]
    for stock in known_stocks:
        if s.startswith(stock):
            return stock
    return None

def main():
    print("=" * 80)
    print(" IMPORT ALL CW + STOCK HISTORY INTO DATABASE")
    print("=" * 80)
    
    if not os.path.isdir(CW_DIR):
        print(f"Directory not found: {CW_DIR}")
        return
    
    csv_files = [f for f in os.listdir(CW_DIR) if f.endswith('_history.csv')]
    print(f"Found {len(csv_files)} CW CSV files in {CW_DIR}")
    
    # Group by underlying stock
    stock_cw_map = {}
    for f in csv_files:
        cw_sym = f.replace('_history.csv', '')
        stock = extract_stock_symbol(cw_sym)
        if stock:
            if stock not in stock_cw_map:
                stock_cw_map[stock] = []
            stock_cw_map[stock].append((cw_sym, os.path.join(CW_DIR, f)))
    
    print(f"Mapped to {len(stock_cw_map)} underlying stocks: {', '.join(sorted(stock_cw_map.keys()))}")
    
    # Check which stocks already have history in DB
    existing_stocks = pd.read_sql("SELECT DISTINCT symbol FROM stock_history", engine)['symbol'].tolist()
    print(f"Stocks already in DB: {', '.join(existing_stocks)}")
    
    # Download missing stock histories
    missing_stocks = [s for s in stock_cw_map.keys() if s not in existing_stocks]
    if missing_stocks:
        print(f"\nDownloading history for {len(missing_stocks)} missing stocks: {', '.join(missing_stocks)}")
        from datetime import datetime, timedelta
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')
        
        for stock in missing_stocks:
            try:
                import time
                time.sleep(0.5)
                q = vnstock.Quote(symbol=stock)
                hist = q.history(start=start_date, end=end_date)
                if not hist.empty:
                    if 'time' in hist.columns and 'date' not in hist.columns:
                        hist = hist.rename(columns={'time': 'date'})
                    hist['date'] = pd.to_datetime(hist['date']).dt.strftime('%Y-%m-%d')
                    for col in ['open','high','low','close']:
                        if col in hist.columns:
                            hist[col] = hist[col] * 1000
                    hist.insert(0, 'symbol', stock)
                    hist[['symbol','date','open','high','low','close','volume']].to_sql(
                        'stock_history', engine, if_exists='append', index=False
                    )
                    print(f"  Imported {stock}: {len(hist)} rows")
            except Exception as e:
                print(f"  Failed {stock}: {e}")
    
    # Import CW histories
    existing_cw = pd.read_sql("SELECT DISTINCT symbol FROM cw_history", engine)['symbol'].tolist()
    imported = 0
    skipped = 0
    
    for stock, cw_list in stock_cw_map.items():
        for cw_sym, csv_path in cw_list:
            if cw_sym in existing_cw:
                skipped += 1
                continue
            try:
                df = pd.read_csv(csv_path)
                if df.empty or 'close' not in df.columns:
                    continue
                # Ensure standard columns
                if 'symbol' not in df.columns:
                    df.insert(0, 'symbol', cw_sym)
                cols_needed = ['symbol','date','open','high','low','close','volume']
                cols_available = [c for c in cols_needed if c in df.columns]
                df[cols_available].to_sql('cw_history', engine, if_exists='append', index=False)
                imported += 1
            except Exception as e:
                print(f"  Failed to import {cw_sym}: {e}")
    
    print(f"\nCW Import complete: {imported} new, {skipped} already existed")
    
    # Final counts
    cw_count = pd.read_sql("SELECT COUNT(DISTINCT symbol) as c FROM cw_history", engine).iloc[0]['c']
    stock_count = pd.read_sql("SELECT COUNT(DISTINCT symbol) as c FROM stock_history", engine).iloc[0]['c']
    print(f"\nDatabase now contains:")
    print(f"  CW symbols: {cw_count}")
    print(f"  Stock symbols: {stock_count}")

if __name__ == "__main__":
    main()
