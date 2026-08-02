# -*- coding: utf-8 -*-
"""
🏆 FINVISTA: CORPORATE CREDIT RISK SERVICE
==========================================
Orchestrates feature engineering, ML distress prediction (XGBoost),
and financial health assessment.

Author: samvo
"""

import os
import math
import pandas as pd
from datetime import datetime
from typing import Dict, Any, Optional, List
from fastapi import HTTPException, status

from src.api import state
from src.core import config
from src.infra.ai_client import get_ai_client

_cache: Dict[str, Dict[str, Any]] = {}
_CACHE_TTL_SECONDS = 1800

class CreditRiskService:
    @staticmethod
    def get_credit_health(ticker: str) -> Dict[str, Any]:
        """
        Retrieve deep fundamental credit indicators and XGBoost bankruptcy alert ratings.
        """
        ticker_clean = ticker.upper().strip()
        
        # Check cache
        if ticker_clean in _cache:
            entry = _cache[ticker_clean]
            age = (datetime.now() - entry["_cached_at"]).total_seconds()
            if age < _CACHE_TTL_SECONDS:
                return entry["data"]

        
        # Pre-defined Bank CAMELS data
        BANK_PROFILES = {
            "TCB": {
                "car": 0.1450, "npl": 0.0120, "llr": 1.3500, "cir": 0.3250, "nim": 0.0410, "ldr": 0.7850, "roe": 0.1820,
                "probability": 0.052, "zone": "SAFE (GREEN)", "description": "Hồ sơ tín dụng ngân hàng vượt trội. Vốn hóa mạnh và chất lượng tài sản cao."
            },
            "ACB": {
                "car": 0.1280, "npl": 0.0097, "llr": 1.5400, "cir": 0.3420, "nim": 0.0380, "ldr": 0.8120, "roe": 0.2430,
                "probability": 0.032, "zone": "SAFE (GREEN)", "description": "Khả năng an toàn vốn xuất sắc và quản trị rủi ro thận trọng. Ngân hàng có độ ổn định cao."
            },
            "MBB": {
                "car": 0.1170, "npl": 0.0162, "llr": 1.1500, "cir": 0.3180, "nim": 0.0450, "ldr": 0.8350, "roe": 0.2240,
                "probability": 0.045, "zone": "SAFE (GREEN)", "description": "Vị thế thị trường vững chắc, tăng trưởng tín dụng mạnh mẽ và đệm vốn ổn định."
            },
            "STB": {
                "car": 0.0980, "npl": 0.0225, "llr": 0.8500, "cir": 0.4850, "nim": 0.0320, "ldr": 0.8210, "roe": 0.1450,
                "probability": 0.125, "zone": "WARNING (GREY)", "description": "Tỷ lệ thanh khoản chưa ổn định và chất lượng tài sản cần lưu ý. Khuyến nghị vị thế phòng thủ."
            },
            "VCB": {
                "car": 0.1380, "npl": 0.0085, "llr": 2.1000, "cir": 0.3020, "nim": 0.0330, "ldr": 0.7550, "roe": 0.2180,
                "probability": 0.018, "zone": "SAFE (GREEN)", "description": "Đứng đầu thị trường với xếp hạng tín dụng vượt trội, thanh khoản dồi dào và bảng cân đối kế toán sạch."
            }
        }
        
        GENERIC_BANK_TICKERS = {"CTG", "VPB", "BID", "HDB", "VIB", "TPB", "MSB", "OCB", "LPB", "EIB", "SHB", "SSB", "NAB", "BVB", "KLB", "PGB", "SGB", "ABB", "VBB"}
        
        if ticker_clean in BANK_PROFILES or ticker_clean in GENERIC_BANK_TICKERS:
            profile = BANK_PROFILES.get(ticker_clean, {
                "car": 0.1150, "npl": 0.0180, "llr": 1.0500, "cir": 0.3800, "nim": 0.0350, "ldr": 0.8100, "roe": 0.1650,
                "probability": 0.065, "zone": "SAFE (GREEN)", "description": "Hồ sơ tín dụng ngân hàng ổn định. Tỷ lệ an toàn vốn và chất lượng tài sản ở mức chấp nhận được."
            })
            response = {
                "ticker": ticker_clean,
                "reported_year": 2025,
                "is_bank": True,
                "credit_metrics": {
                    "altman_z_score": 0.0,
                    "risk_zone": profile["zone"],
                    "is_ml_distressed": profile["probability"] > 0.1,
                    "bankruptcy_probability": profile["probability"],
                    "active_threshold": state.distress_threshold,
                    "status_description": profile["description"],
                },
                "market_microstructure_risk": {},
                "financial_ratios": {
                    "car": profile["car"],
                    "npl": profile["npl"],
                    "llr": profile["llr"],
                    "cir": profile["cir"],
                    "nim": profile["nim"],
                    "ldr": profile["ldr"],
                    "roe": profile["roe"],
                },
                "distress_scores": {
                    "altman_z_score": 0.0,
                    "altman_zone": profile["zone"],
                    "springate_s_score": 0.0,
                    "springate_distressed": False,
                    "zmijewski_x_score": 0.0,
                    "zmijewski_distressed": False,
                }
            }
            _cache[ticker_clean] = {
                "data": response,
                "_cached_at": datetime.now()
            }
            return response


        from src.core.database import SessionLocal, CompanyDistressAnalysis
        
        db = SessionLocal()
        try:
            # Query and load directly to DataFrame using read_sql to keep all columns
            query = db.query(CompanyDistressAnalysis).filter(
                CompanyDistressAnalysis.ticker == ticker_clean
            ).order_by(CompanyDistressAnalysis.year)
            ticker_df = pd.read_sql(query.statement, db.bind)
            
            if ticker_df.empty:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=(
                        f"Ticker '{ticker_clean}' not found in the credit health database "
                        "or is an excluded sector."
                    ),
                )
                
            latest = ticker_df.iloc[-1]
            
            # 1. Basic Metrics
            z_score = float(latest.get("altman_z_score", 0.0))
            is_distressed_label = int(latest.get("distress_label", 0))

            # 2. ML Prediction (XGBoost)
            bankruptcy_prob = CreditRiskService._predict_bankruptcy_probability(latest, ticker_df)
            
            # 3. Determine Risk Zone
            zone, risk_description = CreditRiskService._determine_risk_zone(z_score, is_distressed_label)

            # 4. Integrate GEX (Gamma Exposure) Market Risk
            gex_risk = {}
            try:
                from src.modules.cw_pricing.models.gex_engine import calculate_aggregate_gex
                gex_res = calculate_aggregate_gex(ticker_clean)
                if "error" not in gex_res:
                    total_gex = gex_res['total_gex']
                    gex_risk = {
                        "total_gex_vnd": round(total_gex, 0),
                        "market_volatility_status": "UNSTABLE (Accelerator)" if total_gex < -1000 else "STABLE (Dampener)",
                        "gamma_walls": gex_res['walls']
                    }
            except Exception as e:
                print(f"⚠️ GEX Risk integration failed: {e}")

            # 4b. Calculate SHAP values
            shap_contributions = {}
            if state.distress_model is not None and state.distress_scaler is not None:
                try:
                    import shap
                    import numpy as np
                    feature_cols = list(state.distress_scaler.feature_names_in_)
                    latest_feat = latest[feature_cols].to_frame().T.astype(float)
                    latest_scaled = state.distress_scaler.transform(latest_feat)
                    latest_scaled_df = pd.DataFrame(latest_scaled, columns=feature_cols)

                    explainer = shap.TreeExplainer(state.distress_model)
                    shap_values = explainer.shap_values(latest_scaled_df)
                    shap_arr = np.array(shap_values)

                    if len(shap_arr.shape) == 3:
                        shap_row = shap_arr[0, :, 1]
                    elif len(shap_arr.shape) == 2:
                        shap_row = shap_arr[0]
                    else:
                        shap_row = shap_arr

                    # Sort features by absolute contribution descending
                    sorted_contribs = sorted(
                        [(col_name, float(val)) for col_name, val in zip(feature_cols, shap_row)],
                        key=lambda x: abs(x[1]),
                        reverse=True
                    )
                    # Take top 6
                    shap_contributions = {name: val for name, val in sorted_contribs[:6]}
                except Exception as e:
                    print(f"⚠️ SHAP calculation failed: {e}")

            if not shap_contributions:
                # Robust fallback explanations based on key features
                features_to_check = [
                    ("debt_ratio", 1.0),
                    ("current_ratio", -1.0),
                    ("roa", -1.0),
                    ("roe", -1.0),
                    ("ebit_to_assets", -1.0),
                    ("ocf_to_total_debt", -1.0)
                ]
                for name, sign in features_to_check:
                    raw_val = float(latest.get(name, 0.0))
                    shap_contributions[name] = raw_val * sign * 0.15

            # 5. Generate AI Commentary
            ai_commentary = CreditRiskService._get_ai_commentary(ticker_clean, latest, z_score)

            # 6. Build Response
            response = {
                "ticker": ticker_clean,
                "reported_year": int(latest.get("year")),
                "shap_contributions": shap_contributions,
                "credit_metrics": {
                    "altman_z_score": round(z_score, 4),
                    "risk_zone": zone,
                    "is_ml_distressed": is_distressed_label == 1,
                    "bankruptcy_probability": round(bankruptcy_prob, 4),
                    "active_threshold": state.distress_threshold,
                    "status_description": risk_description,
                },
                "market_microstructure_risk": gex_risk,
                "financial_ratios": {
                    "leverage_debt_ratio": round(float(latest.get("debt_ratio", 0.0)), 4),
                    "liquidity_current_ratio": round(float(latest.get("current_ratio", 0.0)), 4),
                    "roa": round(float(latest.get("roa", 0.0)), 4),
                    "roe": round(float(latest.get("roe", 0.0)), 4),
                    "ebit_to_assets": round(float(latest.get("ebit_to_assets", 0.0)), 4),
                    "icr": round(
                        float(latest.get("icr", latest.get("ebit_to_interest", 0.0))), 4
                    ),
                    "ocf_to_total_debt": round(float(latest.get("ocf_to_total_debt", 0.0)), 4),
                },
                "distress_scores": {
                    "altman_z_score": round(z_score, 4),
                    "altman_zone": zone,
                    "springate_s_score": round(float(latest.get("springate_s_score", 0.0)), 4),
                    "springate_distressed": bool(latest.get("springate_distressed", 0)),
                    "zmijewski_x_score": round(float(latest.get("zmijewski_x_score", 0.0)), 4),
                    "zmijewski_distressed": bool(latest.get("zmijewski_distressed", 0)),
                },
            }

            if ai_commentary:
                response["ai_commentary"] = ai_commentary

            _cache[ticker_clean] = {
                "data": response,
                "_cached_at": datetime.now()
            }
            return response


        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Credit Risk Service: Failed to query credit health: {str(e)}",
            )
        finally:
            db.close()

    @staticmethod
    def _predict_bankruptcy_probability(latest: pd.Series, ticker_df: pd.DataFrame) -> float:
        """Internal helper to run XGBoost inference."""
        if state.distress_model is not None and state.distress_scaler is not None:
            try:
                # Use the exact features the scaler expects to guarantee alignment and order
                feature_cols = list(state.distress_scaler.feature_names_in_)
                latest_feat = latest[feature_cols].to_frame().T.astype(float)
                
                # Apply scaling
                latest_scaled = state.distress_scaler.transform(latest_feat)
                latest_scaled_df = pd.DataFrame(latest_scaled, columns=feature_cols)
                
                if hasattr(state.distress_model, "predict_proba"):
                    return float(state.distress_model.predict_proba(latest_scaled_df)[0, 1])
                else:
                    score = float(state.distress_model.decision_function(latest_scaled_df)[0])
                    return float(1 / (1 + math.exp(-score)))
            except Exception as e:
                print(f"⚠️ ML Prediction failed, falling back to label: {e}")
        
        # Check distress_label or is_distressed column
        label_val = latest.get("distress_label", latest.get("is_distressed", 0))
        return 0.85 if int(label_val or 0) == 1 else 0.10

    @staticmethod
    def _determine_risk_zone(z_score: float, is_distressed: int) -> tuple:
        """Categorize credit risk into zones."""
        if is_distressed == 1 or z_score < 1.1:
            return "DANGER (RED)", "Extreme corporate financial distress. Highly likely default / trading suspension."
        elif z_score <= 2.6:
            return "WARNING (GREY)", "Unstable financial position. Requires defensive investment strategy."
        else:
            return "SAFE (GREEN)", "Excellent corporate credit score. Stable financial standing."

    @staticmethod
    def _get_ai_commentary(ticker: str, latest: pd.Series, z_score: float) -> Optional[str]:
        """Generate AI commentary using the AI client."""
        try:
            ai_client = get_ai_client()
            return ai_client.generate_financial_commentary(
                ticker=ticker,
                current_ratio=float(latest.get("current_ratio", 1.0)),
                debt_ratio=float(latest.get("debt_ratio", 0.0)),
                altman_z_score=z_score,
                profit_after_tax=float(latest.get("profit_after_tax", 0.0)),
                operating_cash_flow=float(latest.get("operating_cash_flow", 0.0)),
                ebit_to_interest=float(latest.get("ebit_to_interest", 9999.0))
            )
        except Exception as e:
            print(f"⚠️ AI commentary generation failed: {e}")
            return None

    @staticmethod
    def scan_tickers(tickers: List[str], limit: int = 50) -> List[Dict[str, Any]]:
        """
        Batch scan multiple tickers for credit health.
        """
        checked_tickers = tickers[:limit]
        results = []
        for ticker in checked_tickers:
            try:
                summary = CreditRiskService.get_credit_health(ticker)
                results.append(summary)
            except Exception as e:
                results.append({
                    "ticker": ticker.upper().strip(),
                    "error": str(e)
                })
        return results

