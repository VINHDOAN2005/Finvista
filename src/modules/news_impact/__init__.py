# -*- coding: utf-8 -*-
"""
News Impact Module — dual-layer pipeline (CPCS + CW).
"""
from .service import NewsImpactService
from .pipeline import run_full_pipeline, run_event_study

__all__ = [
    "NewsImpactService",
    "run_full_pipeline",
    "run_event_study",
]
