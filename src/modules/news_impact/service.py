# -*- coding: utf-8 -*-
"""
FINVISTA: NEWS IMPACT SERVICE
==============================
Unified service layer — dual-layer pipeline (CPCS + CW), API, AI Committee integration.
"""

from __future__ import annotations

import os
import joblib
import numpy as np
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from src.core.utils import logger

NEWS_ML_MODEL_PATH = os.path.join("data", "processed", "news_ml_model.joblib")
_cache: Dict[str, Dict[str, Any]] = {}
_CACHE_TTL_SECONDS = 1800


def _is_cache_valid(key: str) -> bool:
    if key not in _cache:
        return False
    age = (datetime.now() - _cache[key]["_cached_at"]).total_seconds()
    return age < _CACHE_TTL_SECONDS


class NewsImpactService:
    """
    Public API:
        get_news_impact(ticker)       → lightweight sentiment summary
        get_ml_signal(ticker)         → ML outperform probability
        run_full_pipeline(...)        → complete B1→B2→B3 dual-layer pipeline
        run_event_study(sym, date)    → single-event case study
    """

    _model = None

    @classmethod
    def _load_model(cls):
        if cls._model is None and os.path.exists(NEWS_ML_MODEL_PATH):
            try:
                cls._model = joblib.load(NEWS_ML_MODEL_PATH)
                logger.info(f"✅ [NewsImpactService] Loaded ML model")
            except Exception as e:
                logger.warning(f"⚠️ [NewsImpactService] ML load failed: {e}")
        return cls._model

    # ── Full pipeline ─────────────────────────────────────────────────────

    @staticmethod
    def run_full_pipeline(
        symbol: str = None,
        keyword: str = None,
        event_date: str = None,
        min_events: int = 3,
        horizons: Optional[List[int]] = None,
        train_ml: bool = False,
        skip_report: bool = True,
    ) -> Dict[str, Any]:
        from src.modules.news_impact.pipeline import run_full_pipeline

        return run_full_pipeline(
            symbol=symbol,
            keyword=keyword,
            event_date=event_date,
            min_events=min_events,
            horizons=horizons,
            train_ml=train_ml,
            skip_report=skip_report,
        )

    @staticmethod
    def run_event_study(symbol: str, event_date: str, keyword: str = None) -> Dict[str, Any]:
        from src.modules.news_impact.pipeline import run_event_study

        return run_event_study(symbol=symbol, event_date=event_date, keyword=keyword)

    # ── Lightweight API reads ─────────────────────────────────────────────

    @staticmethod
    def get_news_impact(ticker: str, days: int = 90, run_pipeline: bool = False) -> Dict[str, Any]:
        cache_key = f"impact_{ticker.upper()}_{days}_{run_pipeline}"
        if _is_cache_valid(cache_key):
            return {k: v for k, v in _cache[cache_key].items() if not k.startswith("_")}

        ticker_clean = ticker.upper().strip()
        result = NewsImpactService._fetch_news_summary(ticker_clean, days)

        ml_signal = NewsImpactService.get_ml_signal(ticker_clean)
        result["ml_outperform_probability"] = ml_signal.get("probability")
        result["ml_model_available"] = ml_signal.get("model_available", False)

        if run_pipeline:
            pipeline_result = NewsImpactService.run_full_pipeline(
                symbol=ticker_clean, min_events=1, skip_report=True
            )
            if pipeline_result.get("status") == "ok":
                result["car_summary"] = pipeline_result.get("summary", {}).get("cpcs_car_summary")
                result["cw_car_summary"] = pipeline_result.get("summary", {}).get("cw_car_summary")
                result["cw_basket"] = pipeline_result.get("cw_basket_summaries", {}).get(ticker_clean)
                result["latest_exposure"] = (
                    pipeline_result.get("exposures", [])[-1]
                    if pipeline_result.get("exposures")
                    else None
                )
            else:
                result["pipeline_note"] = pipeline_result.get("reason", "pipeline_unavailable")

        result["_cached_at"] = datetime.now()
        _cache[cache_key] = result
        return {k: v for k, v in result.items() if not k.startswith("_")}

    @staticmethod
    def get_ml_signal(ticker: str) -> Dict[str, Any]:
        model = NewsImpactService._load_model()
        if model is None:
            return {
                "probability": None,
                "sentiment": "UNKNOWN",
                "model_available": False,
                "note": "Chạy pipeline với --train-ml để tạo model.",
            }

        ticker_clean = ticker.upper().strip()
        try:
            features = NewsImpactService._build_realtime_features(ticker_clean)
            if features is None:
                return {
                    "probability": None,
                    "sentiment": "UNKNOWN",
                    "model_available": True,
                    "note": f"Không đủ dữ liệu giá cho {ticker_clean}.",
                }

            prob = float(model.predict_proba([features])[0][1])
            sentiment = "BULLISH" if prob >= 0.60 else "BEARISH" if prob <= 0.40 else "NEUTRAL"
            return {
                "probability": round(prob, 4),
                "sentiment": sentiment,
                "model_available": True,
                "note": f"Xác suất outperform 5 ngày: {prob:.1%}",
            }
        except Exception as e:
            return {
                "probability": None,
                "sentiment": "UNKNOWN",
                "model_available": True,
                "note": str(e),
            }

    @staticmethod
    def get_ticker_sentiment_score(ticker: str, days: int = 30) -> float:
        summary = NewsImpactService._fetch_news_summary(ticker, days)
        if summary["news_count"] == 0:
            return 0.0
        bd = summary.get("sentiment_breakdown", {})
        return round(bd.get("POSITIVE", 0) / 100 - bd.get("NEGATIVE", 0) / 100, 4)

    @staticmethod
    def _fetch_news_summary(ticker: str, days: int) -> Dict[str, Any]:
        from src.core.database import SessionLocal, CorporateNews

        cutoff_date = (datetime.now() - timedelta(days=days)).date()
        db = SessionLocal()
        try:
            news_records = (
                db.query(CorporateNews)
                .filter(CorporateNews.symbol == ticker, CorporateNews.date >= str(cutoff_date))
                .order_by(CorporateNews.date.desc())
                .all()
            )
            if not news_records:
                return {
                    "ticker": ticker,
                    "period_days": days,
                    "news_count": 0,
                    "sentiment_breakdown": {"POSITIVE": 0, "NEGATIVE": 0, "NEUTRAL": 0},
                    "recent_news": [],
                    "car_summary": None,
                }

            sentiments = [r.sentiment for r in news_records if getattr(r, "sentiment", None)]
            total = max(len(sentiments), 1)
            breakdown = {
                "POSITIVE": round(sentiments.count("POSITIVE") / total * 100, 1),
                "NEGATIVE": round(sentiments.count("NEGATIVE") / total * 100, 1),
                "NEUTRAL": round(sentiments.count("NEUTRAL") / total * 100, 1),
            }
            recent = [
                {
                    "date": str(r.date),
                    "title": r.title,
                    "category": getattr(r, "category", ""),
                    "sentiment": getattr(r, "sentiment", "NEUTRAL"),
                    "source": getattr(r, "source", ""),
                }
                for r in news_records[:5]
            ]
            return {
                "ticker": ticker,
                "period_days": days,
                "news_count": len(news_records),
                "sentiment_breakdown": breakdown,
                "recent_news": recent,
                "car_summary": None,
            }
        except Exception as e:
            logger.error(f"DB fetch failed for {ticker}: {e}")
            return {
                "ticker": ticker,
                "period_days": days,
                "news_count": 0,
                "sentiment_breakdown": {},
                "recent_news": [],
                "car_summary": None,
                "note": str(e),
            }
        finally:
            db.close()

    @staticmethod
    def _build_realtime_features(ticker: str) -> Optional[List[float]]:
        from src.core.database import SessionLocal, StockHistoricalPrice, CorporateNews

        db = SessionLocal()
        try:
            records = (
                db.query(StockHistoricalPrice)
                .filter(StockHistoricalPrice.symbol == ticker)
                .order_by(StockHistoricalPrice.date.asc())
                .all()
            )
            if len(records) < 35:
                return None

            closes = np.array([r.close for r in records], dtype=float)
            volumes = np.array([r.volume for r in records], dtype=float)
            daily_returns = np.diff(closes) / closes[:-1]
            idx = len(closes) - 1

            vol_10d = np.std(daily_returns[idx - 10: idx]) if idx >= 10 else 0.0
            vol_20d = np.std(daily_returns[idx - 20: idx]) if idx >= 20 else 0.0
            vol_30d = np.std(daily_returns[idx - 30: idx]) if idx >= 30 else 0.0

            def mom(n):
                return (closes[idx - 1] - closes[idx - 1 - n]) / closes[idx - 1 - n] if idx > n else 0.0

            vol_avg = np.mean(volumes[idx - 30: idx]) if idx >= 30 else np.mean(volumes)
            vol_ratio_1d = volumes[idx - 1] / vol_avg if vol_avg > 0 else 1.0
            vol_ratio_5d = np.mean(volumes[idx - 5: idx]) / vol_avg if vol_avg > 0 else 1.0

            latest = (
                db.query(CorporateNews)
                .filter(CorporateNews.symbol == ticker)
                .order_by(CorporateNews.date.desc())
                .first()
            )
            sent = getattr(latest, "sentiment", "NEUTRAL") if latest else "NEUTRAL"

            return [
                1.0 if sent == "POSITIVE" else 0.0,
                1.0 if sent == "NEGATIVE" else 0.0,
                1.0 if sent == "NEUTRAL" else 0.0,
                vol_10d, vol_20d, vol_30d,
                mom(1), mom(5), mom(10), mom(20),
                vol_ratio_1d, vol_ratio_5d,
                vol_30d, mom(5),
            ]
        finally:
            db.close()
