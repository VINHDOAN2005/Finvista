# -*- coding: utf-8 -*-
"""Shared API runtime state: distress model registry and pipeline cache."""

import os
import json as _json
import joblib

from src.core import config

distress_model = None
distress_scaler = None
distress_threshold = 0.5

pipeline_cache = {
    "data": None,
    "last_scanned": None,
}


def load_distress_models() -> None:
    """Load credit risk model artifacts at application startup."""
    global distress_model, distress_scaler, distress_threshold
    try:
        distress_model = joblib.load(config.BEST_DISTRESS_MODEL)
        distress_scaler = joblib.load(config.SCALER_ARTIFACT)
        thr_cfg_path = config.THRESHOLD_CONFIG
        if os.path.exists(thr_cfg_path):
            with open(thr_cfg_path) as f:
                distress_threshold = _json.load(f).get("active_threshold", 0.5)
    except Exception as e:
        print(f"[API] ⚠️ Could not load distress model: {e}")
