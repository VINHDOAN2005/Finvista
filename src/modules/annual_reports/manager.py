# -*- coding: utf-8 -*-
"""
💼 ANNUAL REPORT MANAGER
========================
Handles loading/parsing the Zenodo index CSV, extracting files from local ZIP archives,
and running OCR / RAG QA on PDF text via Gemini.

Author: samvo
"""

import os
import logging
import zipfile
import pandas as pd
from pathlib import Path
from pypdf import PdfReader
from io import BytesIO
from typing import List, Dict, Any, Optional

from src.infra.ai_client import get_ai_client
from src.modules.annual_reports.scraper import CafeFReportScraper

logger = logging.getLogger(__name__)

# Base paths
BASE_DIR = Path(__file__).resolve().parents[3]
INDEX_PATH = BASE_DIR / "data" / "raw" / "annual_reports" / "file_index_full.csv"
LOCAL_PDF_DIR = BASE_DIR / "data" / "processed" / "bctc_pdfs"

class AnnualReportManager:
    def __init__(self):
        self.index_df = None
        self._load_index()
        self.scraper = CafeFReportScraper()
        
        # Load local annual reports ZIP directory path from env
        self.zip_dir = os.getenv("ANNUAL_REPORTS_DIR")
        if self.zip_dir:
            self.zip_dir = Path(self.zip_dir)
        else:
            self.zip_dir = BASE_DIR / "data" / "raw" / "annual_reports"

    def _load_index(self):
        """Loads Zenodo index CSV if it exists."""
        if INDEX_PATH.exists():
            try:
                self.index_df = pd.read_csv(INDEX_PATH)
                logger.info(f"Loaded Zenodo index from {INDEX_PATH} with {len(self.index_df)} records.")
            except Exception as e:
                logger.error(f"Failed to load Zenodo index: {e}")
        else:
            logger.warning(f"Zenodo index not found at {INDEX_PATH}")

    def list_available_reports(self, ticker: str) -> List[Dict[str, Any]]:
        """Lists all reports available for a ticker in both Zenodo index and local cache."""
        reports = []
        ticker_upper = ticker.upper()

        # 1. Look up in Zenodo index
        if self.index_df is not None:
            matches = self.index_df[self.index_df['ticker_folder'].str.upper() == ticker_upper]
            for _, row in matches.iterrows():
                zip_filename = f"vn_bctn_{row['archive_period']}.zip"
                zip_exists = False
                if self.zip_dir:
                    zip_exists = (self.zip_dir / zip_filename).exists()

                reports.append({
                    'source': 'zenodo',
                    'year': int(row['year_full']),
                    'quarter': 5, # Zenodo consists of Annual Reports (NAM)
                    'file_name': row['file_name'],
                    'relative_path': row['relative_path'],
                    'archive_period': row['archive_period'],
                    'zip_exists': zip_exists,
                    'downloaded': False # Handled by actual existence
                })

        # 2. Look up in CafeF downloaded folder
        ticker_local_dir = LOCAL_PDF_DIR / ticker_upper
        if ticker_local_dir.exists():
            for pdf_file in ticker_local_dir.glob("*.pdf"):
                # Parse metadata from filename: SYMBOL_YEAR_TAGS_ORIGINALNAME.pdf
                name_parts = pdf_file.stem.split("_")
                year = None
                quarter = 0
                
                # Simple heuristical extraction of year and quarter
                for part in name_parts:
                    if part.isdigit() and len(part) == 4:
                        year = int(part)
                    elif part.startswith("Q") and part[1:].isdigit():
                        quarter = int(part[1:])
                    elif part == "NAM":
                        quarter = 5
                    elif part == "BAN":
                        quarter = 6

                # Avoid duplicate entries
                exists = any(r['year'] == year and r['quarter'] == quarter for r in reports)
                if not exists:
                    reports.append({
                        'source': 'cafef',
                        'year': year or 0,
                        'quarter': quarter,
                        'file_name': pdf_file.name,
                        'relative_path': str(pdf_file.relative_to(BASE_DIR)),
                        'archive_period': None,
                        'zip_exists': False,
                        'downloaded': True
                    })
                    
        # Sort by year desc
        reports.sort(key=lambda x: (x['year'], x['quarter']), reverse=True)
        return reports

    def get_report_pdf_bytes(self, ticker: str, year: int, quarter: int = 5) -> Optional[bytes]:
        """Gets PDF file bytes either from local ZIP (Zenodo) or downloaded folder (CafeF)."""
        ticker_upper = ticker.upper()

        # 1. Check in CafeF local cache directory
        ticker_local_dir = LOCAL_PDF_DIR / ticker_upper
        if ticker_local_dir.exists():
            # Match by year and quarter pattern in filename
            q_pattern = f"Q{quarter}" if 1 <= quarter <= 4 else ("NAM" if quarter == 5 else ("BAN" if quarter == 6 else ""))
            for pdf_file in ticker_local_dir.glob("*.pdf"):
                stem_upper = pdf_file.stem.upper()
                if f"_{year}_" in stem_upper and (not q_pattern or q_pattern in stem_upper):
                    try:
                        return pdf_file.read_bytes()
                    except Exception as e:
                        logger.error(f"Error reading local PDF file {pdf_file}: {e}")

        # 2. Check in Zenodo ZIP archives
        if self.index_df is not None:
            matches = self.index_df[
                (self.index_df['ticker_folder'].str.upper() == ticker_upper) &
                (self.index_df['year_full'] == year)
            ]
            if not matches.empty:
                row = matches.iloc[0]
                zip_filename = f"vn_bctn_{row['archive_period']}.zip"
                if self.zip_dir:
                    zip_path = self.zip_dir / zip_filename
                    if zip_path.exists():
                        try:
                            logger.info(f"Extracting {row['relative_path']} from ZIP archive {zip_path}")
                            with zipfile.ZipFile(zip_path, 'r') as z:
                                return z.read(row['relative_path'])
                        except Exception as e:
                            logger.error(f"Failed to read from zip file {zip_path}: {e}")
                    else:
                        logger.warning(f"Zip file {zip_filename} not found in {self.zip_dir}")

        return None

    def extract_text_from_pdf_bytes(self, pdf_bytes: bytes) -> str:
        """Extracts text content from PDF bytes using pypdf."""
        try:
            reader = PdfReader(BytesIO(pdf_bytes))
            text_pages = []
            for i, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text:
                    text_pages.append(f"--- TRANG {i+1} ---\n{page_text}")
            return "\n\n".join(text_pages)
        except Exception as e:
            logger.error(f"Failed to extract text from PDF bytes: {e}")
            return ""

    def download_from_cafef(self, ticker: str, year: int, quarter: int = 5) -> bool:
        """Downloads report from CafeF API for a ticker, year and quarter on-demand."""
        ticker_upper = ticker.upper()
        reports = self.scraper.fetch_report_metadata(ticker_upper, start_year=year)
        
        # Filter for the specific year and quarter
        target_report = None
        for r in reports:
            if r['year'] == year and r['quarter'] == quarter:
                target_report = r
                break
                
        # If not exact match but they asked for Annual Report (NAM), try to match NAM
        if not target_report and quarter == 5:
            for r in reports:
                if r['year'] == year and r['quarter'] in [5, 0]: # 5 or 0 could represent annual
                    target_report = r
                    break

        if not target_report:
            logger.warning(f"Could not find report matching {ticker_upper} for year {year}, quarter {quarter} on CafeF.")
            return False

        save_path = LOCAL_PDF_DIR / ticker_upper / target_report['filename']
        return self.scraper.download_pdf(target_report['url'], save_path)

    def query_report(self, ticker: str, year: int, quarter: int, question: str) -> str:
        """Extracts report text, injects it into Gemini prompt context to answer user's question."""
        pdf_bytes = self.get_report_pdf_bytes(ticker, year, quarter)
        
        if not pdf_bytes:
            # Try to auto-download from CafeF
            logger.info(f"Report not found locally. Attempting to download {ticker} {year} Q{quarter} from CafeF...")
            success = self.download_from_cafef(ticker, year, quarter)
            if success:
                pdf_bytes = self.get_report_pdf_bytes(ticker, year, quarter)
            
        if not pdf_bytes:
            return f"❌ Không tìm thấy Báo cáo tài chính cho {ticker} năm {year} (Quý {quarter}). Vui lòng tải file ZIP Zenodo tương ứng hoặc kiểm tra kết nối mạng để tải trực tiếp từ CafeF."

        text_content = self.extract_text_from_pdf_bytes(pdf_bytes)
        database_fallback = False
        
        if not text_content or len(text_content.strip()) < 100:
            try:
                from src.core.database import SessionLocal, CompanyFinancial, CompanyDistressAnalysis
                db_sess = SessionLocal()
                try:
                    f = db_sess.query(CompanyFinancial).filter(CompanyFinancial.ticker == ticker.upper(), CompanyFinancial.year == year).first()
                    d = db_sess.query(CompanyDistressAnalysis).filter(CompanyDistressAnalysis.ticker == ticker.upper(), CompanyDistressAnalysis.year == year).first()
                    
                    if f or d:
                        database_fallback = True
                        text_content = f"DỮ LIỆU ĐỊNH LƯỢNG THỰC TẾ TRONG HỆ THỐNG CHO DOANH NGHIỆP {ticker.upper()} NĂM {year}:\n"
                        if f:
                            text_content += (
                                f"- Doanh thu thuần: {f.net_revenue:,.0f} VND\n"
                                f"- Lợi nhuận sau thuế: {f.profit_after_tax:,.0f} VND\n"
                                f"- Tổng tài sản: {f.total_assets:,.0f} VND\n"
                                f"- Tổng nợ phải trả: {f.total_liabilities:,.0f} VND\n"
                                f"- Vốn chủ sở hữu: {f.total_equity:,.0f} VND\n"
                                f"- Dòng tiền từ HĐKD (OCF): {f.operating_cash_flow:,.0f} VND\n"
                                f"- Vốn hóa thị trường: {f.market_cap:,.0f} VND\n"
                            )
                        if d:
                            text_content += (
                                f"- Tỷ số thanh toán hiện hành: {d.current_ratio:.2f}\n"
                                f"- Tỷ lệ nợ/tài sản: {d.debt_ratio:.2f}\n"
                                f"- Tỷ suất sinh lời ROAA: {d.roaa*100:.2f}%\n"
                                f"- Tỷ suất sinh lời ROAE: {d.roae*100:.2f}%\n"
                                f"- Chỉ số Altman Z-Score: {d.altman_z_score:.2f}\n"
                                f"- Xác suất vỡ nợ Merton PD: {d.merton_pd*100:.2f}%\n"
                            )
                finally:
                    db_sess.close()
            except Exception:
                pass
                
            if not database_fallback:
                return f"❌ Trích xuất văn bản từ tệp PDF của {ticker} năm {year} thất bại hoặc tệp chỉ chứa hình ảnh chưa quét OCR."

        # Limit text content to prevent context overflow
        max_chars = 150000
        if len(text_content) > max_chars:
            text_content = text_content[:max_chars] + "\n\n[...Nội dung bị cắt bớt để tối ưu hóa hiệu năng...]"

        ai_client = get_ai_client()
        
        # Build strict prompt for RAG
        intro_text = (
            f"[LƯU Ý QUAN TRỌNG: Tệp PDF báo cáo tài chính là định dạng scan hình ảnh chưa quét OCR. Bạn đang trả lời dựa trên các dữ liệu số liệu định lượng thực tế trong cơ sở dữ liệu được cung cấp dưới đây.]"
            if database_fallback
            else f"Dưới đây là nội dung Báo cáo tài chính/Báo cáo thường niên của doanh nghiệp {ticker} năm {year} (Quý {quarter})."
        )
        
        prompt = f"""Bạn là một chuyên gia phân tích tài chính cao cấp (CFA).
{intro_text}
Hãy trả lời câu hỏi của người dùng dựa trên thông tin chính xác trong văn bản báo cáo này. 

LƯU Ý QUAN TRỌNG:
1. Chỉ sử dụng thông tin có trong văn bản được cung cấp. Nếu văn bản không có thông tin, hãy báo rõ không tìm thấy trong báo cáo.
2. Trình bày số liệu tài chính cụ thể dưới dạng bảng Markdown nếu có so sánh nhiều thông tin.
3. In đậm các số liệu quan trọng (`**số liệu**`).
4. Viết bằng tiếng Việt chuyên nghiệp, rõ ràng.

VĂN BẢN BÁO CÁO:
{text_content}

CÂU HỎI: {question}
"""
        messages = [{"role": "user", "content": prompt}]
        response = ai_client.chat(messages=messages)
        
        return response
