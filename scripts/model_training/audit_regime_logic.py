# -*- coding: utf-8 -*-
"""
🔬 FINVISTA: REGIME VALIDATION AUDIT (BATCH TEST)
================================================
Tests the KAIROS 8-state model across a batch of symbols and 
performs statistical validation of state characteristics.
"""

import pandas as pd
import numpy as np
import os
import sys

# Ensure project root is in path
sys.path.append(os.getcwd())

from src.modules.regime_analysis.indicators.regime_detector import RegimeDetector
from src.core.database import engine

def run_batch_regime_audit(symbols: list, days: int = 1000):
    print(f"🚀 Bắt đầu Audit hệ thống Regime cho {len(symbols)} mã...")
    
    all_results = []
    
    for symbol in symbols:
        try:
            query = f"SELECT date, close FROM stock_history WHERE symbol='{symbol}' ORDER BY date ASC"
            df = pd.read_sql(query, engine)
            if df.empty: continue
            
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            df = df.tail(days)
            
            # Calculate regimes
            res = RegimeDetector.calculate_kairos_regimes(df['close'])
            res['symbol'] = symbol
            all_results.append(res)
        except Exception as e:
            print(f"⚠️ Lỗi khi xử lý {symbol}: {e}")

    if not all_results:
        print("❌ Không có dữ liệu để Audit.")
        return

    full_df = pd.concat(all_results)
    
    # Statistical Validation: Group by Regime
    audit_stats = full_df.groupby('regime').agg({
        'momentum': ['mean', 'std'],
        'vol_30': ['mean', 'std'],
        'p_turbulent': ['mean'],
        'price': 'count'
    })
    
    audit_stats.columns = ['_'.join(col).strip() for col in audit_stats.columns.values]
    audit_stats = audit_stats.rename(columns={'price_count': 'frequency'})
    audit_stats['pct_total'] = (audit_stats['frequency'] / audit_stats['frequency'].sum()) * 100

    print("\n" + "="*80)
    print(" 📊 BẢNG KIỂM ĐỊNH ĐẶC TÍNH REGIME (CROSS-SYMBOL VALIDATION) ".center(80))
    print("="*80)
    
    # Check if definitions hold:
    # S3 (Strong Trend) should have high absolute momentum
    # S1 (Compression) should have low vol_30
    # S4 (Climax) should have high p_turbulent
    
    print(audit_stats.sort_index().to_string())
    print("-" * 80)
    
    print("\n 🔍 ĐÁNH GIÁ ĐỘ CHUẨN XÁC (LOGIC CHECK):")
    
    s3_mom = audit_stats.loc['S3: Xu_Hướng_Mạnh', 'momentum_mean'] if 'S3: Xu_Hướng_Mạnh' in audit_stats.index else 0
    s1_vol = audit_stats.loc['S1: Nén_Chặt', 'vol_30_mean'] if 'S1: Nén_Chặt' in audit_stats.index else 1
    
    if abs(s3_mom) > 2.0:
        print(" ✅ S3 (Xu hướng mạnh): HỢP LỆ (Momentum trung bình > 2%)")
    else:
        print(" ❌ S3 (Xu hướng mạnh): CẢNH BÁO (Momentum trung bình quá thấp)")
        
    if s1_vol < 0.20:
        print(" ✅ S1 (Nén chặt): HỢP LỆ (Volatility trung bình < 20%)")
    else:
        print(" ❌ S1 (Nén chặt): CẢNH BÁO (Volatility trung bình quá cao)")

    print("="*80 + "\n")

if __name__ == "__main__":
    # Test with VN30 or a subset
    test_symbols = ["FPT", "VHM", "HPG", "VIC", "MSN", "MWG", "TCB", "VCB", "STB", "VNM"]
    run_batch_regime_audit(test_symbols)
