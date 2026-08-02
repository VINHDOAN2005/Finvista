# -*- coding: utf-8 -*-
"""
🕷️ CAFÉF FINANCIAL REPORT SCRAPER
=================================
Downloads financial reports (BCTC) and annual reports (BCTN) for Vietnamese stocks on-demand.
Based on the scrapers from Trading Hub All In One.

Author: samvo
"""

import os
import re
import time
import logging
import requests
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class CafeFReportScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': 'https://cafef.vn/'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def _clean_name(self, name: str) -> str:
        """Sanitize filename to prevent OS/Windows filesystem errors."""
        name = re.sub(r'[\\/*?:"<>|]', "", name)
        name = re.sub(r'\s+', "_", name)
        return name.strip("_")

    def fetch_report_metadata(self, symbol: str, start_year: int = 2000) -> List[Dict[str, Any]]:
        """Queries CafeF Ajax endpoint to fetch listing of available PDF reports."""
        url = f"https://cafef.vn/du-lieu/Ajax/PageNew/FileBCTC.ashx?Symbol={symbol.lower()}&Type=1&Year=0"
        
        try:
            logger.info(f"Querying CafeF reports for symbol: {symbol.upper()}")
            response = self.session.get(url, timeout=20)
            if response.status_code != 200:
                logger.error(f"CafeF API returned status code: {response.status_code}")
                return []
                
            data = response.json()
            if not data.get('Success') or 'Data' not in data:
                logger.warning(f"No report data found for symbol: {symbol}")
                return []
                
            reports = []
            seen_urls = set()

            for item in data['Data']:
                name = item.get('Name', '').strip()
                link = item.get('Link', '')
                year = item.get('Year', 0)
                quarter = item.get('Quarter', 0)  # 1-4: Quý, 5: Năm (BCTN), 6: Bán niên
                
                if year < start_year:
                    continue
                
                if not link or not link.startswith('http') or link in seen_urls:
                    continue
                
                # Tag logic
                tags = []
                name_upper = name.upper()
                
                if 1 <= quarter <= 4:
                    tags.append(f"Q{quarter}")
                elif quarter == 5:
                    tags.append("NAM")
                elif quarter == 6:
                    tags.append("BAN_NIEN")
                
                if "HỢP NHẤT" in name_upper or "HN" in name_upper:
                    tags.append("HN")
                elif "MẸ" in name_upper:
                    tags.append("ME")
                    
                if "KIỂM TOÁN" in name_upper:
                    tags.append("KT")
                elif "SOÁT XÉT" in name_upper:
                    tags.append("SX")
                
                tag_str = "_".join(tags) if tags else f"T{quarter}"
                clean_orig = self._clean_name(name)
                filename = f"{symbol.upper()}_{year}_{tag_str}_{clean_orig}.pdf"
                
                reports.append({
                    'title': name,
                    'url': link,
                    'filename': filename,
                    'year': year,
                    'quarter': quarter,
                    'type': 'annual_report' if quarter == 5 else 'financial_report'
                })
                seen_urls.add(link)

            return reports
        except Exception as e:
            logger.error(f"Error calling CafeF API for {symbol}: {e}")
            return []

    def download_pdf(self, url: str, save_path: Path) -> bool:
        """Downloads PDF to local storage."""
        if save_path.exists() and save_path.stat().st_size > 20480:
            logger.info(f"File already exists (and >20KB), skipping: {save_path.name}")
            return True

        try:
            response = self.session.get(url, stream=True, timeout=60)
            if response.status_code != 200:
                logger.error(f"Failed to download PDF, status code: {response.status_code}")
                return False
            
            # Read first chunk to verify PDF header
            content_iter = response.iter_content(chunk_size=4096)
            try:
                first_chunk = next(content_iter, b'')
            except StopIteration:
                return False
            
            if not first_chunk.startswith(b'%PDF'):
                logger.warning(f"Downloaded content does not look like a PDF: {url}")
                return False
                
            save_path.parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, 'wb') as f:
                f.write(first_chunk)
                for chunk in content_iter:
                    f.write(chunk)
            
            logger.info(f"Downloaded: {save_path.name}")
            return True
        except Exception as e:
            logger.error(f"Failed downloading PDF from {url}: {e}")
            return False
