# -*- coding: utf-8 -*-
"""
🏆 FINVISTA: VIETSTOCK CORPORATE EVENTS & NEWS SCRAPER
=====================================================
Crawls Vietstock for Covered Warrant specific news and underlying stock dividend schedules.
Optimized to avoid redundant crawls for CWs sharing the same underlying security.

Author: samvo
"""

import os
import sys
import requests
import time
import re
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup
import pandas as pd
from sqlalchemy.orm import Session

# Ensure project root is on PYTHONPATH
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.core.database import SessionLocal, CorporateNews, CorporateEvent
from src.modules.cw_pricing.backtest.fetcher import fetch_market_cw_data
from src.core.utils import logger, random_sleep

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
}

def normalize_date(raw: str) -> str:
    """Standardize date strings from Vietstock format (dd/mm/yyyy hh:mm) to YYYY-MM-DD HH:MM."""
    if not raw:
        return ""
    raw = raw.strip()
    # Try dd/mm/yyyy hh:mm
    try:
        match = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})(?:\s+(\d{1,2}:\d{2}))?", raw)
        if match:
            d, m, y, t = match.groups()
            t = t if t else "00:00"
            return f"{y}-{m.zfill(2)}-{d.zfill(2)} {t}"
    except Exception:
        pass
    return raw

class VietstockScraper:
    def __init__(self):
        self.db = SessionLocal()

    def __del__(self):
        if hasattr(self, 'db'):
            self.db.close()

    def get_cw_list(self):
        """Fetch unique underlying symbols and one representative CW for each."""
        try:
            df = fetch_market_cw_data()
            if df.empty:
                return {}
            # Group by underlying and pick the first CW symbol
            mapping = df.groupby('B_MaCPCS')['A_MaCW'].first().to_dict()
            return mapping
        except Exception as e:
            logger.error(f"Error fetching CW list: {e}")
            return {}

    def scrape_cw_page(self, cw_symbol, underlying_symbol, max_pages=30):
        """Scrape news and events for a specific CW/Underlying pair with pagination."""
        logger.info(f"📡 Scraping Vietstock for {underlying_symbol} (via {cw_symbol}) - Deep Crawl ({max_pages} pages)...")
        
        # 1. Scrape News (Underlying Stock)
        self._scrape_paged_content(
            url="https://finance.vietstock.vn/View/StockNewsContentPage",
            code=underlying_symbol,
            category="Cổ phiếu cơ sở",
            target_symbol=underlying_symbol,
            max_pages=max_pages
        )

        # 2. Scrape News (Warrant)
        self._scrape_paged_content(
            url="https://finance.vietstock.vn/View/StockNewsContentPage",
            code=cw_symbol,
            category="Chứng quyền",
            target_symbol=cw_symbol,
            max_pages=max_pages
        )

        # 3. Scrape Events (Underlying Stock)
        self._scrape_paged_events(
            url="https://finance.vietstock.vn/View/StockEventContentPage",
            code=underlying_symbol,
            max_pages=max_pages
        )

    def _scrape_paged_content(self, url, code, category, target_symbol, max_pages):
        """Generic handler for paged news content via POST."""
        for page in range(1, max_pages + 1):
            payload = {
                "code": code,
                "channelID": -1,
                "page": page,
                "pageSize": 10
            }
            try:
                resp = None
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        resp = requests.post(url, headers=HEADERS, data=payload, timeout=25)
                        break
                    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as req_err:
                        if attempt == max_retries - 1:
                            raise req_err
                        time.sleep(attempt * 2 + 2)
                
                if not resp or resp.status_code != 200 or not resp.text.strip():
                    break
                
                soup = BeautifulSoup(resp.content, "html.parser")
                rows = soup.select("table tr")
                if not rows: break
                
                added_in_page = 0
                for row in rows:
                    cols = row.find_all("td")
                    if len(cols) >= 2:
                        date_raw = cols[0].get_text(strip=True)
                        link_el = cols[1].find("a")
                        if link_el:
                            title = link_el.get_text(strip=True)
                            raw_href = link_el['href'] or ""
                            if raw_href.startswith("//"):
                                link = "https:" + raw_href
                            elif raw_href.startswith("/vietstock.vn"):
                                link = "https:/" + raw_href
                            elif raw_href.startswith("/"):
                                link = "https://finance.vietstock.vn" + raw_href
                            else:
                                link = raw_href
                            if self._save_news(target_symbol, title, link, normalize_date(date_raw), category):
                                added_in_page += 1
                
                if added_in_page == 0: # No new items found (all already in DB)
                    break
                    
                random_sleep(1, 2)
            except Exception as e:
                logger.error(f"❌ Error scraping news page {page} for {code}: {e}")
                break

    def _scrape_paged_events(self, url, code, max_pages):
        """Generic handler for paged event content via POST."""
        for page in range(1, max_pages + 1):
            payload = {
                "code": code,
                "channelID": 0, # 0 usually covers all events
                "page": page,
                "pageSize": 10,
                "orderBy": "Date1",
                "orderDir": "DESC"
            }
            try:
                resp = None
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        resp = requests.post(url, headers=HEADERS, data=payload, timeout=25)
                        break
                    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as req_err:
                        if attempt == max_retries - 1:
                            raise req_err
                        time.sleep(attempt * 2 + 2)
                
                if not resp or resp.status_code != 200 or not resp.text.strip():
                    break
                
                soup = BeautifulSoup(resp.content, "html.parser")
                rows = soup.select("table tr")
                if not rows: break
                
                added_in_page = 0
                for row in rows:
                    cols = row.find_all("td")
                    if len(cols) >= 2:
                        date_raw = cols[0].get_text(strip=True)
                        event_desc = cols[1].get_text(strip=True)
                        
                        event_type = "Sự kiện doanh nghiệp"
                        if "cổ tức" in event_desc.lower():
                            event_type = "Cổ tức tiền mặt" if "tiền" in event_desc.lower() else "Cổ tức cổ phiếu"
                        elif "họp" in event_desc.lower():
                            event_type = "Đại hội cổ đông"
                        
                        if self._save_event(code, normalize_date(date_raw).split(" ")[0], event_type, event_desc):
                            added_in_page += 1
                
                if added_in_page == 0:
                    break
                    
                random_sleep(1, 2)
            except Exception as e:
                logger.error(f"❌ Error scraping event page {page} for {code}: {e}")
                break

    def _save_news(self, symbol, title, link, date, category):
        # Check if news exists
        existing = self.db.query(CorporateNews).filter(CorporateNews.link == link).first()
        if not existing:
            news = CorporateNews(
                symbol=symbol,
                title=title,
                link=link,
                date=date,
                category=category,
                source="Vietstock"
            )
            self.db.add(news)
            try:
                self.db.commit()
                return True
            except Exception:
                self.db.rollback()
        return False

    def _save_event(self, ticker, event_date, event_type, description):
        # Check if event exists
        existing = self.db.query(CorporateEvent).filter(
            CorporateEvent.ticker == ticker,
            CorporateEvent.event_date == event_date,
            CorporateEvent.description == description
        ).first()
        
        if not existing:
            event = CorporateEvent(
                ticker=ticker,
                event_date=event_date,
                event_type=event_type,
                description=description
            )
            self.db.add(event)
            try:
                self.db.commit()
                return True
            except Exception:
                self.db.rollback()
        return False

    def run(self, limit=None):
        logger.info("🚀 Starting Vietstock Corporate Events & News Scraper...")
        mapping = self.get_cw_list()
        if not mapping:
            logger.warning("⚠️ No CW symbols found to process.")
            return

        count = 0
        for underlying, cw in mapping.items():
            if limit and count >= limit:
                break
            
            self.scrape_cw_page(cw, underlying)
            count += 1
            random_sleep(2, 4) # Be polite to Vietstock

        logger.info(f"✅ Finished scraping events for {count} underlying assets.")

if __name__ == "__main__":
    scraper = VietstockScraper()
    scraper.run()
