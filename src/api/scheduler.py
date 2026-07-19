# -*- coding: utf-8 -*-
"""Background periodic market scan scheduler."""

import threading
import time
from datetime import datetime

from src.modules.cw_pricing.backtest.run_analysis import run_quant_pipeline_programmatic

# Track whether daily update has been run for today
_daily_update_last_run_date: str = ""


def _run_daily_data_update():
    """
    Incrementally fetch new historical data (stock prices, CW prices, news)
    for dates that are missing from the database. Runs once per trading day.
    """
    try:
        print("📅 [Scheduler] Starting daily incremental data refresh (stock prices, CW history, news)...")
        from src.modules.cw_pricing.etl.daily_updater import run_daily_update
        run_daily_update(update_stocks=True, update_cw=True, update_news=True)
        print("✅ [Scheduler] Daily data refresh completed successfully.")
    except Exception as e:
        print(f"⚠️ [Scheduler] Daily data refresh error: {e}")


def start_periodic_scheduler() -> None:
    global _daily_update_last_run_date

    def scheduler_loop():
        global _daily_update_last_run_date
        time.sleep(10)
        print("🕒 [Scheduler Thread] Starting periodic market scanning background loop...")
        while True:
            try:
                now = datetime.now()
                is_weekday = now.weekday() < 5
                time_str = now.strftime("%H:%M:%S")
                today_str = now.strftime("%Y-%m-%d")
                in_morning = "09:00:00" <= time_str <= "11:30:00"
                in_afternoon = "13:00:00" <= time_str <= "14:45:00"
                # After market close (15:30–17:00): run daily incremental update once per day
                after_close = "15:30:00" <= time_str <= "17:00:00"

                if is_weekday and (in_morning or in_afternoon):
                    print(
                        "🕒 [Scheduler Thread] HOSE Market is open. "
                        "Executing scheduled quantitative scan..."
                    )
                    run_quant_pipeline_programmatic(strategy="balanced")
                    print(
                        "🕒 [Scheduler Thread] Scheduled quantitative scan completed and persisted."
                    )
                    time.sleep(900)

                elif is_weekday and after_close and _daily_update_last_run_date != today_str:
                    # Run daily data update once after market close
                    _daily_update_last_run_date = today_str
                    update_thread = threading.Thread(target=_run_daily_data_update, daemon=True)
                    update_thread.start()
                    time.sleep(300)  # Wait 5 min before next check

                else:
                    time.sleep(300)
            except Exception as e:
                print(f"⚠️ [Scheduler Thread] Error in loop: {e}")
                time.sleep(60)

    t = threading.Thread(target=scheduler_loop, daemon=True)
    t.start()
