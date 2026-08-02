# -*- coding: utf-8 -*-
"""
🏠 FINVISTA: REAL ESTATE SECTOR SPECIALIZED SCORING (Presales-Logic)
==================================================================
Provides specialized health metrics for Real Estate developers (VHM, NVL, PDR...).
Focuses on Projected Cash Flows, Inventory-to-Debt, and Interest Coverage.

Author: samvo
"""

import pandas as pd
from typing import Dict, Any

def score_real_estate_health(ratios: Dict[str, float]) -> float:
    """
    Calculate a specialized health score (0-100) for Real Estate companies.
    Focus: ICR, Inventory/Debt, Pre-sales indicator.
    """
    # 1. Interest Coverage Ratio (ICR) - Trọng số 30%
    # Ngành BĐS nợ nhiều, khả năng trả lãi là sống còn.
    icr = ratios.get('icr', 0)
    score_icr = min(max(icr / 3.0 * 30, 0), 30)

    # 2. Inventory / Total Debt (Chất lượng tài sản) - Trọng số 25%
    # Kiểm tra xem nợ có được bao phủ bởi hàng tồn kho (dự án) không.
    inv_debt = ratios.get('inventory_to_debt', 0)
    score_inv = min(max(inv_debt / 1.5 * 25, 0), 25)

    # 3. Pre-sales Indicator (Người mua trả tiền trước / Nợ) - Trọng số 25%
    # Đây là dòng tiền "để dành", cực kỳ quan trọng tại VN.
    presales = ratios.get('presales_to_debt', 0)
    score_pre = min(max(presales / 0.5 * 25, 0), 25)

    # 4. Debt to Equity (Đòn bẩy) - Trọng số 20%
    de = ratios.get('debt_to_equity', 1.0)
    score_de = min(max((3.0 - de) / (3.0 - 0.5) * 20, 0), 20)

    return score_icr + score_inv + score_pre + score_de

def get_re_metrics_from_df(df_ratios: pd.DataFrame) -> Dict[str, float]:
    """Extract key Real Estate metrics from vnstock ratio DataFrame."""
    if df_ratios.empty:
        return {}
        
    latest_col = df_ratios.columns[-1]
    
    def get_val(item_id):
        row = df_ratios[df_ratios['item_id'] == item_id]
        return float(row[latest_col].iloc[0]) if not row.empty else 0.0

    # Note: Presales in Vietnam reports is often 'Advances from customers' 
    # In vnstock common ratios it might not be explicit, so we use proxies or raw mapping if available.
    # For now, we use standard leverage and liquidity proxies from the ratio table.
    
    metrics = {
        'icr': get_val('debt_coverage'), # Proxy for interest coverage
        'inventory_to_debt': get_val('inventory_turnover') * 0.5, # Heuristic proxy
        'presales_to_debt': get_val('cash_return_on_equity') * 0.2, # Heuristic proxy
        'debt_to_equity': get_val('debt_to_equity')
    }
    
    return metrics
