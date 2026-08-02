# -*- coding: utf-8 -*-
"""
🏆 FINVISTA: REGIME DETECTOR INDICATOR
======================================
Defines the RegimeDetector class for calculating the 8-state market regimes (Kairos v3).
"""

import numpy as np
import pandas as pd
from hmmlearn.hmm import GaussianHMM

class HamiltonMarkovSwitching:
    """
    A 2-state Markov Switching model using GaussianHMM to detect normal vs turbulent regimes.
    """
    def __init__(self):
        self.model = GaussianHMM(n_components=2, covariance_type="diag", n_iter=100, random_state=42)
        self.high_vol_state = 1
        
    def fit(self, returns: np.ndarray):
        x = np.asarray(returns, dtype=float).reshape(-1, 1)
        try:
            self.model.fit(x)
            # Identify the state with higher variance as the turbulent state
            if hasattr(self.model, "_covars_"):
                vols = np.sqrt(np.squeeze(self.model._covars_))
                self.high_vol_state = np.argmax(vols)
        except Exception:
            pass
            
    def predict_probs(self, returns: np.ndarray) -> np.ndarray:
        x = np.asarray(returns, dtype=float).reshape(-1, 1)
        try:
            probs = self.model.predict_proba(x)
            return probs[:, self.high_vol_state]
        except Exception:
            # Fallback probability: higher when absolute returns are higher
            abs_ret = np.abs(returns)
            ma = pd.Series(abs_ret).rolling(20, min_periods=1).mean().values
            fallback = abs_ret / (ma + 1e-8)
            fallback = np.clip(fallback / 2.0, 0.0, 1.0)
            return fallback

class RegimeDetector:
    """
    A class to detect market regimes using advanced metrics.
    """
    def __init__(self):
        pass
        
    def HamiltonMarkovSwitching(self) -> HamiltonMarkovSwitching:
        return HamiltonMarkovSwitching()

    @staticmethod
    def calculate_kairos_regimes(close_series_or_df) -> pd.DataFrame:
        """
        Calculates the 8 KAIROS regimes (S0 to S7) based on close prices.
        """
        if isinstance(close_series_or_df, pd.DataFrame):
            close = close_series_or_df['close']
        else:
            close = close_series_or_df
            
        returns = close.pct_change().fillna(0)
        
        # Fit Hamilton Markov Switching to get probability of turbulence
        hms = HamiltonMarkovSwitching()
        hms.fit(returns.values)
        p_turbulent = hms.predict_probs(returns.values)
        
        # Compute volatility (30-day rolling annualized standard deviation)
        vol_30 = returns.rolling(30).std() * np.sqrt(252)
        vol_30 = vol_30.fillna(vol_30.mean() if not pd.isna(vol_30.mean()) else 0.20)
        
        # Compute momentum (10-day price percentage change)
        momentum = close.pct_change(10) * 100
        momentum = momentum.fillna(0.0)
        
        regimes = []
        for i in range(len(close)):
            v = vol_30.iloc[i]
            m = momentum.iloc[i]
            p_t = p_turbulent[i]
            
            # 8-state mapping logic
            if v < 0.12:
                reg = "S0: Đóng_Băng"
            elif v < 0.20 and abs(m) < 2.0:
                reg = "S1: Nén_Chặt"
            elif v >= 0.20 and abs(m) >= 2.0 and abs(m) < 4.0:
                reg = "S2: Đầu_Xu_Hướng"
            elif abs(m) >= 4.0 and v < 0.35:
                reg = "S3: Xu_Hướng_Mạnh"
            elif abs(m) >= 6.0 and v >= 0.35:
                reg = "S4: Cao_Trào"
            elif p_t > 0.70 and abs(m) < 3.0:
                reg = "S6: Nhiễu_Động"
            elif p_t > 0.50 and abs(m) >= 3.0:
                reg = "S7: Quét_Thanh_Khoản"
            else:
                reg = "S5: Hồi_Quy"
                
            regimes.append(reg)
            
        res = pd.DataFrame({
            'price': close,
            'momentum': momentum,
            'vol_30': vol_30,
            'p_turbulent': p_turbulent,
            'regime': regimes
        }, index=close.index)
        return res
