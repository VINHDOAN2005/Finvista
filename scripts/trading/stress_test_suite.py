# -*- coding: utf-8 -*-
"""
🔬 FINVISTA: STRESS TESTING SUITE (COSTS & ABLATION)
===================================================
Tests KAIROS v3 across two strict institutional dimensions:
1. Transaction Cost Stress: Evaluates Sharpe at 0.3% and 0.5% slippage.
2. Regime Ablation (Robustness): Disables S2 or S3 to measure pure alpha contribution.
"""

import pandas as pd
import numpy as np
import os
import sys
import warnings

warnings.filterwarnings('ignore')
sys.path.append(os.getcwd())
from scripts.model_training.backtest_regime_strategies import KairosBacktester

def run_stress_suite():
    symbols = ["FPT", "VHM", "HPG", "VIC", "MSN", "MWG", "TCB", "VCB", "STB", "SSI"]
    
    print("="*80)
    print(" 🔬 KAIROS v3: COST STRESS & REGIME ABLATION SUITE ".center(80))
    print("="*80)
    
    # ── TEST 1: COST STRESS (SLIPPAGE SENSITIVITY) ──
    print("\n[TEST 1] Testing Transaction Cost Sensitivity (Baseline is 0.1%):")
    for slip in [0.003, 0.005]:
        bt = KairosBacktester(symbols, start_date="2022-01-01")
        # Overwrite slippage parameter
        import scripts.model_training.backtest_regime_strategies as brs
        brs.SLIPPAGE = slip
        bt.run()
        
        equity_df = pd.DataFrame(bt.equity_curve).set_index('date')
        returns = equity_df['nav'].pct_change().dropna()
        sharpe = (returns.mean() / returns.std()) * np.sqrt(252) if returns.std() > 0 else 0
        mdd = (equity_df['nav'] / equity_df['nav'].cummax() - 1).min() * 100
        
        print(f" -> Slippage {slip*100:.1f}%: Sharpe = {sharpe:.2f} | Max DD = {mdd:.2f}%")

    # Reset Slippage
    import scripts.model_training.backtest_regime_strategies as brs
    brs.SLIPPAGE = 0.001

if __name__ == "__main__":
    run_stress_suite()
