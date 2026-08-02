# -*- coding: utf-8 -*-
import pytest
import os
import pandas as pd
from unittest.mock import patch, MagicMock
from pathlib import Path
from src.modules.annual_reports.manager import AnnualReportManager

def test_annual_report_manager_load_index():
    # Test loading Zenodo index
    with patch("pathlib.Path.exists", return_value=True), \
         patch("pandas.read_csv") as mock_read_csv:
         
        mock_df = pd.DataFrame([{
            'record_id': 'AAH_2024_e28d74e0',
            'ticker_folder': 'AAH',
            'ticker_file': 'AAH',
            'year_full': 2024,
            'archive_period': '2021_2025',
            'document_type': 'annual_report',
            'file_name': 'AAH_24CN_BCTN.pdf',
            'relative_path': 'AAH/AAH_24CN_BCTN.pdf',
            'file_size_bytes': 9035689,
            'file_size_mb': 8.62,
            'sha256': 'e28d74e0538669d8c5cf28210292794e65d00bbe06a41b9da22f3917c6d8cde2',
            'status': 'ok',
            'notes': ''
        }])
        mock_read_csv.return_value = mock_df
        
        manager = AnnualReportManager()
        assert manager.index_df is not None
        assert len(manager.index_df) == 1
        
        reports = manager.list_available_reports("AAH")
        assert len(reports) == 1
        assert reports[0]['year'] == 2024
        assert reports[0]['source'] == 'zenodo'

def test_download_from_cafef_success():
    manager = AnnualReportManager()
    
    mock_reports = [
        {
            'title': 'Báo cáo thường niên năm 2024',
            'url': 'https://cafef.vn/bctn.pdf',
            'filename': 'FPT_2024_NAM_BCTN.pdf',
            'year': 2024,
            'quarter': 5,
            'type': 'annual_report'
        }
    ]
    
    with patch.object(manager.scraper, "fetch_report_metadata", return_value=mock_reports), \
         patch.object(manager.scraper, "download_pdf", return_value=True) as mock_download:
         
        success = manager.download_from_cafef("FPT", 2024, 5)
        assert success is True
        mock_download.assert_called_once()
