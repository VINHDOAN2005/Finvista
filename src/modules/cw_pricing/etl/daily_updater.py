# -*- coding: utf-8 -*-
"""
📅 FINVISTA: DAILY DATA UPDATER
================================
Incrementally fetches new historical price data (stock + CW) and corporate news
from the last recorded date in DB to today. Designed to run automatically after
market close each day via the scheduler.

Only fetches the DELTA (missing dates) to be fast and not re-download existing data.

Author: samvo
"""
import os
import sys
import time
import logging
from datetime import datetime, timedelta

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

logger = logging.getLogger("daily_updater")

# ─── Suppress vnstock banners ──────────────────────────────────────────────────
import contextlib
with contextlib.redirect_stdout(open(os.devnull, 'w')), \
     contextlib.redirect_stderr(open(os.devnull, 'w')):
    try:
        import vnstock
    except Exception:
        vnstock = None


def _insert_rows_safe(df, table: str, engine) -> int:
    """
    Insert rows using raw SQL INSERT ... ON CONFLICT (symbol, date) DO NOTHING.
    This avoids UniqueViolation from the auto-increment id sequence on PostgreSQL.
    Returns the number of rows actually inserted.
    """
    from sqlalchemy import text as sa_text
    if df.empty:
        return 0

    cols = [c for c in ['symbol', 'date', 'open', 'high', 'low', 'close', 'volume'] if c in df.columns]
    col_list = ", ".join(cols)
    placeholders = ", ".join([f":{c}" for c in cols])

    inserted = 0
    with engine.begin() as conn:
        for _, row in df[cols].iterrows():
            params = {c: row[c] for c in cols}
            result = conn.execute(
                sa_text(
                    f"INSERT INTO {table} ({col_list}) VALUES ({placeholders}) "
                    f"ON CONFLICT DO NOTHING"
                ),
                params
            )
            inserted += result.rowcount
    return inserted


def update_stock_prices(days_back: int = 30):
    """
    Fetch new stock prices for all symbols in stock_history.
    Only inserts rows newer than the latest date in the DB for each symbol.
    """
    try:
        import pandas as pd
        from src.core.database import engine

        # Get all distinct symbols and their latest date
        rows = pd.read_sql(
            "SELECT symbol, MAX(date) as latest FROM stock_history GROUP BY symbol",
            engine
        )
        if rows.empty:
            logger.info("[StockUpdate] No symbols found in DB, skipping.")
            return

        today_str = datetime.now().strftime('%Y-%m-%d')
        start_fallback = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')

        updated_count = 0
        for _, row in rows.iterrows():
            symbol = row['symbol']
            latest_in_db = str(row['latest']) if row['latest'] else start_fallback

            # Only fetch if there's a gap
            if latest_in_db >= today_str:
                continue

            # Fetch from day after latest
            fetch_from = (datetime.strptime(latest_in_db[:10], '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')

            try:
                if vnstock is None:
                    continue
                q = vnstock.Quote(symbol=symbol)
                hist = q.history(start=fetch_from, end=today_str)
                if hist is None or (hasattr(hist, 'empty') and hist.empty):
                    continue

                # Normalize columns
                if 'time' in hist.columns and 'date' not in hist.columns:
                    hist = hist.rename(columns={'time': 'date'})
                hist['date'] = pd.to_datetime(hist['date']).dt.strftime('%Y-%m-%d')

                # Filter only truly new rows
                hist = hist[hist['date'] > latest_in_db]
                if hist.empty:
                    continue

                # Scale prices (vnstock returns in thousands)
                for col in ['open', 'high', 'low', 'close']:
                    if col in hist.columns:
                        hist[col] = hist[col] * 1000

                hist.insert(0, 'symbol', symbol)
                n = _insert_rows_safe(hist, 'stock_history', engine)
                logger.info(f"[StockUpdate] {symbol}: +{n} rows (up to {hist['date'].max()})")
                if n > 0:
                    updated_count += 1
                time.sleep(0.3)

            except Exception as e:
                logger.warning(f"[StockUpdate] Failed for {symbol}: {e}")

        logger.info(f"[StockUpdate] Done. Updated {updated_count} symbols.")

    except Exception as e:
        logger.error(f"[StockUpdate] Unexpected error: {e}")


def update_cw_prices(days_back: int = 30):
    """
    Fetch new CW prices for all symbols in cw_history.
    Only inserts rows newer than the latest date in DB.
    Optimized: only updates currently active CW symbols from market_opportunities.
    """
    try:
        import pandas as pd
        from src.core.database import engine

        # Try to find active CW symbols from market_opportunities
        try:
            active_df = pd.read_sql("SELECT DISTINCT symbol FROM market_opportunities", engine)
            active_symbols = set(active_df['symbol'].tolist()) if not active_df.empty else set()
            logger.info(f"[CWUpdate] Found {len(active_symbols)} active CW symbols in market_opportunities.")
        except Exception as e:
            logger.warning(f"[CWUpdate] Could not load active CW symbols from market_opportunities: {e}. Will fall back to all symbols.")
            active_symbols = set()

        rows = pd.read_sql(
            "SELECT symbol, MAX(date) as latest FROM cw_history GROUP BY symbol",
            engine
        )
        if rows.empty:
            logger.info("[CWUpdate] No CW symbols found in DB, skipping.")
            return

        # Filter only active symbols if we have them
        if active_symbols:
            original_len = len(rows)
            rows = rows[rows['symbol'].isin(active_symbols)]
            logger.info(f"[CWUpdate] Filtered CW symbols to update from {original_len} to {len(rows)} active symbols.")

        if rows.empty:
            logger.info("[CWUpdate] No active CW symbols need updating, skipping.")
            return

        today_str = datetime.now().strftime('%Y-%m-%d')
        start_fallback = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')

        updated_count = 0
        for _, row in rows.iterrows():
            symbol = row['symbol']
            latest_in_db = str(row['latest']) if row['latest'] else start_fallback

            if latest_in_db >= today_str:
                continue

            fetch_from = (datetime.strptime(latest_in_db[:10], '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')

            try:
                if vnstock is None:
                    continue
                q = vnstock.Quote(symbol=symbol)
                hist = q.history(start=fetch_from, end=today_str)
                if hist is None or (hasattr(hist, 'empty') and hist.empty):
                    continue

                if 'time' in hist.columns and 'date' not in hist.columns:
                    hist = hist.rename(columns={'time': 'date'})
                hist['date'] = pd.to_datetime(hist['date']).dt.strftime('%Y-%m-%d')
                hist = hist[hist['date'] > latest_in_db]
                if hist.empty:
                    continue

                hist.insert(0, 'symbol', symbol)
                n = _insert_rows_safe(hist, 'cw_history', engine)
                logger.info(f"[CWUpdate] {symbol}: +{n} rows (up to {hist['date'].max()})")
                if n > 0:
                    updated_count += 1
                time.sleep(0.2)

            except Exception as e:
                logger.warning(f"[CWUpdate] Failed for {symbol}: {e}")

        logger.info(f"[CWUpdate] Done. Updated {updated_count} CW symbols.")

    except Exception as e:
        logger.error(f"[CWUpdate] Unexpected error: {e}")


def update_corporate_news(limit_per_underlying: int = 5):
    """
    Scrape new corporate news from Vietstock for all active underlying stocks.
    Only adds articles not already in DB (deduplicated by URL/link).
    """
    try:
        from src.modules.credit_risk.etl.vietstock_scraper import VietstockScraper
        scraper = VietstockScraper()
        # Fetch news for all underlyings (no limit) - deduplication by link prevents re-adding
        scraper.run(limit=None)
        logger.info("[NewsUpdate] Vietstock news scrape completed.")
    except Exception as e:
        logger.error(f"[NewsUpdate] Failed: {e}")


def run_daily_update(update_stocks: bool = True, update_cw: bool = True, update_news: bool = True):
    """
    Main entry point for the daily incremental data refresh.
    Safe to call even if data is already up-to-date (idempotent).
    """
    logger.info("=" * 60)
    logger.info("📅 [DailyUpdater] Starting incremental data refresh...")
    logger.info(f"   Stocks: {update_stocks}, CW history: {update_cw}, News: {update_news}")
    logger.info("=" * 60)

    if update_stocks:
        logger.info("[DailyUpdater] Updating stock historical prices...")
        update_stock_prices(days_back=30)

    if update_cw:
        logger.info("[DailyUpdater] Updating CW historical prices...")
        update_cw_prices(days_back=30)

    if update_news:
        logger.info("[DailyUpdater] Scraping new corporate news...")
        update_corporate_news()

    logger.info("✅ [DailyUpdater] Daily incremental update complete.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    run_daily_update()
