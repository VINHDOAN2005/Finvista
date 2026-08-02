# -*- coding: utf-8 -*-
"""
🚀 FINVISTA: MASTER ORCHESTRATOR
================================
The "Brain" that coordinates all scheduled tasks:
- Ingestion (Price & News)
- Quant Analysis
- Credit Evaluation
- AI Committee Reviews
- Alert Dispatching (Telegram)
- Automated Execution (Paper Trading)
"""

import os
import sys
import time
import asyncio
from datetime import datetime
from src.core.utils import logger
from src.modules.credit_risk.etl.vietstock_scraper import VietstockScraper
from src.modules.regime_analysis.etl.macro_scraper import fetch_macro_indicators
from src.modules.cw_pricing.backtest.run_analysis import run_quant_pipeline_programmatic
from src.infra.news_alerts import dispatch_news_alerts, dispatch_event_alerts
from src.infra.telegram_alerts import send_telegram_alert_batch, send_credit_distress_alert_batch
from src.modules.trading_engine.ai_committee_service import AICommitteeService
from src.modules.trading_engine.paper_trader import scan_and_trade

class FinvistaOrchestrator:
    def __init__(self):
        self.last_full_run = None
        self.last_news_crawl = None
        self.ai_committee = AICommitteeService()

    def run_morning_prep(self):
        """Pre-market preparation (08:30 - 09:00)."""
        logger.info("🌅 [Orchestrator] Running Morning Preparation...")
        
        # 1. Fetch Macro Data
        fetch_macro_indicators()
        
        # 2. Deep News Crawl
        scraper = VietstockScraper()
        scraper.run(limit=10) # Process top 10 underlyings deeply
        
        # 3. Dispatch Alerts
        dispatch_news_alerts(limit=5)
        dispatch_event_alerts(limit=3)
        
        logger.info("✅ [Orchestrator] Morning Prep Complete.")

    async def _process_signals_with_ai(self, buy_signals):
        """Process STRONG BUY signals through the AI Committee."""
        approved_signals = []
        for signal in buy_signals:
            symbol = signal.get("A_MaCW")
            logger.info(f"🤖 [Orchestrator] Sending {symbol} to AI Committee for debate...")
            try:
                ai_result = await self.ai_committee.analyze_opportunity(symbol)
                decision = ai_result.get("decision", {})
                action = decision.get("decision", "SKIP")
                confidence = decision.get("confidence_score", 0)
                
                if action in ["STRONG BUY", "BUY"] and confidence >= 70:
                    logger.info(f"✅ [Orchestrator] AI Committee APPROVED {symbol} (Score: {confidence}).")
                    approved_signals.append(signal)
                else:
                    logger.warning(f"❌ [Orchestrator] AI Committee REJECTED {symbol} (Action: {action}, Score: {confidence}).")
            except Exception as e:
                logger.error(f"⚠️ [Orchestrator] AI Committee analysis failed for {symbol}: {e}")
                
        return approved_signals

    def run_market_loop(self):
        """Intra-day market monitoring loop."""
        now = datetime.now()
        is_weekday = now.weekday() < 5
        time_str = now.strftime("%H:%M:%S")
        
        in_morning = "09:15:00" <= time_str <= "11:30:00"
        in_afternoon = "13:00:00" <= time_str <= "14:45:00"
        
        # Override for testing if needed
        is_market_open = in_morning or in_afternoon
        if not is_weekday:
            is_market_open = False

        # If you want to force it to run during development, you can comment out the return
        # if not is_market_open: return 

        logger.info(f"📈 [Orchestrator] Market Open ({time_str}). Running live analysis...")
        
        # 1. Run Quant Pipeline
        # This implicitly includes the Credit Risk mapping via SQLite
        df = run_quant_pipeline_programmatic(strategy="balanced")
        
        # 2. Identify signals & Trigger AI Committee -> Execution
        if df is not None and not df.empty:
            buy_signals = df[df['U_Signal'].isin(['STRONG BUY'])].to_dict('records')
            
            if buy_signals:
                logger.info(f"🎯 [Orchestrator] Found {len(buy_signals)} STRONG BUY candidates. Initiating AI Committee debate...")
                # Run the AI debate
                approved_signals = asyncio.run(self._process_signals_with_ai(buy_signals[:3])) # Limit to top 3 to save time/API

                
                if approved_signals:
                    logger.info("🚀 [Orchestrator] AI Committee approved candidates. Proceeding to Automated Execution...")
                    # 3. Execute Trades
                    approved_symbols = [s.get("A_MaCW") for s in approved_signals]
                    actions = scan_and_trade(force=True, approved_symbols=approved_symbols)
                    for act in actions:
                        logger.info(f"  * {act}")
                    
                    # 4. Telegram Alerts
                    # We can send an alert about the approved signals
                    send_telegram_alert_batch(approved_signals, []) 
            else:
                # Always run scan_and_trade to process Stop Losses / Take Profits for existing portfolio
                scan_and_trade(force=True)
            
        # 5. Top-Down Volatility Breakout Scanner
        try:
            from src.modules.cw_pricing.backtest.scan_stock_setups import main as run_breakout_scanner
            run_breakout_scanner()
        except Exception as e:
            logger.error(f"⚠️ [Orchestrator] Breakout Scanner failed: {e}")

        # 6. Quick News Refresh (every 30 mins)
        if self.last_news_crawl is None or (now - self.last_news_crawl).total_seconds() > 1800:
            scraper = VietstockScraper()
            scraper.run(limit=5)
            dispatch_news_alerts(limit=3)
            self.last_news_crawl = now

    def start(self):
        """Start the continuous orchestration service."""
        logger.info("🚀 Finvista Master Orchestrator Started.")
        
        # Initial run
        self.run_morning_prep()
        
        try:
            while True:
                self.run_market_loop()
                time.sleep(300) # Check every 5 minutes
        except KeyboardInterrupt:
            logger.info("🛑 Orchestrator stopped.")

if __name__ == "__main__":
    orchestrator = FinvistaOrchestrator()
    orchestrator.start()
