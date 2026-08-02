# -*- coding: utf-8 -*-
"""
📈 FINVISTA: FINANCIAL SECTOR SPECIALIZED SCORING (NON-BANK)
==========================================================
Provides specialized health metrics for Securities and Insurance companies.
Implements risk evaluation logic for non-bank financial institutions.

Author: samvo
"""

import pandas as pd
from typing import Dict, Any

def score_securities_health(ratios: Dict[str, float]) -> float:
    """
    Scoring for Securities companies (SSI, VND, VCI...).
    Focus: Net Margin, ROE, Debt/Assets, Liquidity.
    """
    # 1. Net Margin (Biên lãi ròng) - 30%
    # Securities have high margins if efficient. Target > 30%
    net_margin = ratios.get('net_margin', 0)
    score_margin = min(max(net_margin / 0.50 * 30, 0), 30)

    # 2. ROE - 30%
    roe = ratios.get('roe', 0)
    score_roe = min(max(roe / 0.20 * 30, 0), 30)

    # 3. Debt/Assets (Đòn bẩy) - 20%
    # Securities often use debt for margin lending. Target < 60%
    debt_assets = ratios.get('debt_to_assets', 0.5)
    score_debt = min(max((0.8 - debt_assets) / (0.8 - 0.3) * 20, 0), 20)

    # 4. Cash Ratio (Thanh khoản) - 20%
    cash_ratio = ratios.get('cash_ratio', 0)
    score_cash = min(max(cash_ratio / 1.5 * 20, 0), 20)

    return score_margin + score_roe + score_debt + score_cash

def score_insurance_health(ratios: Dict[str, float]) -> float:
    """
    Scoring for Insurance companies (BVH, PGI, MIG...).
    Focus: ROE, Net Margin, Debt Coverage.
    """
    # 1. ROE - 40%
    roe = ratios.get('roe', 0)
    score_roe = min(max(roe / 0.15 * 40, 0), 40)

    # 2. Net Margin - 30%
    net_margin = ratios.get('net_margin', 0)
    score_margin = min(max(net_margin / 0.15 * 30, 0), 30)

    # 3. Debt Coverage - 30%
    # Insurance companies need strong coverage.
    debt_cov = ratios.get('debt_coverage', 1.0)
    score_cov = min(max(debt_cov / 2.0 * 30, 0), 30)

    return score_roe + score_margin + score_cov

def get_fi_metrics_from_df(df_ratios: pd.DataFrame) -> Dict[str, float]:
    """Extract common financial ratios for non-bank FIs."""
    if df_ratios.empty:
        return {}
    
    latest_col = df_ratios.columns[-1]
    
    def get_val(item_id):
        row = df_ratios[df_ratios['item_id'] == item_id]
        if not row.empty:
            val = float(row[latest_col].iloc[0])
            # vnstock usually provides ratios as percentages
            return val / 100.0 if abs(val) > 0.5 else val
        return None

    metrics = {
        'roe': get_val('roe'),
        'roa': get_val('roa'),
        'net_margin': get_val('net_margin'),
        'debt_to_assets': get_val('debt_to_assets'),
        'cash_ratio': get_val('cash_ratio'),
        'debt_coverage': get_val('debt_coverage')
    }
    return metrics
