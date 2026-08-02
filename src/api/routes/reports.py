# -*- coding: utf-8 -*-
"""
🔌 FINVISTA: REPORTS API ROUTER
================================
Provides endpoints for listing, downloading, and querying (RAG) financial and annual reports.

Author: samvo
"""

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from src.modules.annual_reports.manager import AnnualReportManager

router = APIRouter(prefix="/api/reports", tags=["Reports & RAG"])
manager = AnnualReportManager()

class DownloadRequest(BaseModel):
    ticker: str
    year: int
    quarter: Optional[int] = 5 # Default to annual report

class ChatReportRequest(BaseModel):
    ticker: str
    year: int
    quarter: Optional[int] = 5
    question: str

@router.get("/index")
def get_reports_index(ticker: str = Query(..., description="Stock ticker symbol (e.g. FPT, VRE)")):
    """Lists all available reports for a ticker from Zenodo index and local cache."""
    try:
        reports = manager.list_available_reports(ticker)
        return {
            "ticker": ticker.upper(),
            "count": len(reports),
            "reports": reports
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load reports index for {ticker}: {str(e)}"
        )

@router.post("/download")
def download_report(request: DownloadRequest):
    """Downloads a report from CafeF API for a ticker, year, and quarter."""
    try:
        success = manager.download_from_cafef(
            ticker=request.ticker,
            year=request.year,
            quarter=request.quarter
        )
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Could not find or download report for {request.ticker} year {request.year} Q{request.quarter} on CafeF."
            )
        return {
            "status": "success",
            "message": f"Successfully downloaded report for {request.ticker} {request.year} Q{request.quarter}."
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Download failed: {str(e)}"
        )

@router.post("/chat")
def chat_with_report(request: ChatReportRequest):
    """Answers a question using the annual/financial report text of a company as context."""
    try:
        answer = manager.query_report(
            ticker=request.ticker,
            year=request.year,
            quarter=request.quarter,
            question=request.question
        )
        return {
            "ticker": request.ticker.upper(),
            "year": request.year,
            "quarter": request.quarter,
            "question": request.question,
            "answer": answer
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat failed: {str(e)}"
        )
