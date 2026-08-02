# -*- coding: utf-8 -*-
"""
🏦 FINVISTA: BANKING SECTOR SPECIALIZED SCORING (CAMELS-lite)
============================================================
Provides specialized health metrics for Banking institutions (ACB, VCB, MBB...).
Implements NPL, NIM, CASA, and CAR evaluation logic.

Author: samvo
"""

import pandas as pd
from typing import Dict, Any

def score_bank_health(ratios: Dict[str, float]) -> float:
    """
    Calculate a specialized health score (0-100) for banks.
    Based on NIM, NPL, CASA, CAR, and CIR.
    """
    # 1. NIM (Hiệu quả biên lãi) - Trọng số 20%
    nim = ratios.get('nim')
    score_nim = min(max((nim - 0.02) / (0.045 - 0.02) * 20, 0), 20) if nim is not None else 10

    # 2. NPL (Chất lượng nợ) - Trọng số 20%
    npl = ratios.get('npl')
    score_npl = min(max((0.05 - npl) / (0.05 - 0.01) * 20, 0), 20) if npl is not None else 10

    # 3. CASA (Chi phí vốn) - Trọng số 15%
    casa = ratios.get('casa')
    score_casa = min(max((casa - 0.1) / (0.4 - 0.1) * 15, 0), 15) if casa is not None else 7

    # 4. CAR (An toàn vốn) - Trọng số 20%
    car = ratios.get('car')
    score_car = min(max((car - 0.08) / (0.14 - 0.08) * 20, 0), 20) if car is not None else 10

    # 5. CIR (Hiệu quả vận hành) - Trọng số 15%
    cir = ratios.get('cir')
    score_cir = min(max((0.6 - cir) / (0.6 - 0.3) * 15, 0), 15) if cir is not None else 7

    # 6. ROE (Hiệu quả vốn) - Trọng số 10%
    roe = ratios.get('roe')
    score_roe = min(max(roe / 0.25 * 10, 0), 10) if roe is not None else 5

    return score_nim + score_npl + score_casa + score_car + score_cir + score_roe

def get_bank_metrics_from_df(df_ratios: pd.DataFrame, ticker: str) -> Dict[str, float]:
    """
    Extract key banking metrics from vnstock ratio DataFrame.
    """
    if df_ratios.empty:
        return {}
        
    latest_col = df_ratios.columns[-1]
    
    def get_val(item_id):
        row = df_ratios[df_ratios['item_id'] == item_id]
        if not row.empty:
            val = float(row[latest_col].iloc[0])
            # vnstock usually provides ratios as percentages (e.g. 3.5 for 3.5%)
            # We convert to decimal
            return val / 100.0 if abs(val) > 0.5 else val
        return None

    metrics = {
        'nim': get_val('net_interest_margin_nim'),
        'npl': get_val('bad_debt_ratio') or get_val('npl_ratio'),
        'casa': get_val('casa_ratio'),
        'car': get_val('capital_adequacy_ratio_car'),
        'cir': get_val('cost_income_ratio_cir'),
        'roe': get_val('roe')
    }
    
    return metrics
