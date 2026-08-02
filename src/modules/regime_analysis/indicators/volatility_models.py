# -*- coding: utf-8 -*-
"""
FINVISTA: VOLATILITY MODELS (EWMA & GARCH)
===========================================
Implementations of EWMA and GARCH(1,1) for volatility forecasting and scaling.
Theory: John C. Hull - Risk Management and Financial Institutions (Ch. 10)

Author: samvo
"""

import numpy as np
import pandas as pd
import warnings
from arch import arch_model

warnings.filterwarnings('ignore')

class VolatilityModeler:
    """
    A math core class to calculate, forecast, and scale volatility using EWMA and GARCH(1,1).
    """
    
    @staticmethod
    def ewma_variance(returns: pd.Series, lambda_: float = 0.94) -> pd.Series:
        """
        Calculate conditional variance using the Exponentially Weighted Moving Average (EWMA) model.
        Theory: RiskMetrics approach where lambda is typically 0.94 for daily data.
        σ_n^2 = λ * σ_{n-1}^2 + (1 - λ) * u_{n-1}^2
        """
        returns_sq = returns ** 2
        var_series = np.zeros_like(returns_sq)
        
        # Initialize the first variance as the sample variance of the first 20 days (if available) or the whole series
        initial_var = returns.head(20).var() if len(returns) >= 20 else returns.var()
        var_series[0] = initial_var
        
        for i in range(1, len(returns_sq)):
            var_series[i] = lambda_ * var_series[i-1] + (1 - lambda_) * returns_sq.iloc[i-1]
            
        return pd.Series(var_series, index=returns.index)

    @staticmethod
    def garch_variance(returns: pd.Series, p: int = 1, q: int = 1) -> pd.Series:
        """
        Calculate conditional variance using the GARCH(p,q) model with Student's t distribution.
        Handles fat tails and mean reversion.
        """
        # Scale returns for optimization stability
        scaled_returns = returns * 100.0
        
        # Fit GARCH
        model = arch_model(scaled_returns, mean='Constant', vol='GARCH', p=p, q=q, dist='studentst')
        try:
            res = model.fit(disp='off')
            # Extract conditional volatility and square it for variance, then unscale
            cond_var = (res.conditional_volatility / 100.0) ** 2
            return pd.Series(cond_var, index=returns.index)
        except Exception as e:
            print(f"⚠️ GARCH fit failed: {e}. Falling back to EWMA.")
            return VolatilityModeler.ewma_variance(returns)

    @staticmethod
    def forecast_volatility(returns: pd.Series, method: str = 'GARCH') -> float:
        """
        Forecast the T+1 annualized volatility.
        """
        if len(returns) < 50:
            return returns.std() * np.sqrt(252) # Fallback to standard historical vol
            
        if method.upper() == 'GARCH':
            scaled_returns = returns * 100.0
            model = arch_model(scaled_returns, mean='Constant', vol='GARCH', p=1, q=1, dist='studentst')
            try:
                res = model.fit(disp='off')
                forecast = res.forecast(horizon=1)
                next_day_var = forecast.variance.iloc[-1, 0]
                # Unscale and annualize
                return (np.sqrt(next_day_var) / 100.0) * np.sqrt(252)
            except:
                pass
                
        # EWMA Forecast (T+1 variance is just the formula applied to the last known point)
        var_series = VolatilityModeler.ewma_variance(returns)
        next_day_var = 0.94 * var_series.iloc[-1] + (1 - 0.94) * (returns.iloc[-1] ** 2)
        return np.sqrt(next_day_var) * np.sqrt(252)

    @staticmethod
    def get_volatility_scaling_factors(returns: pd.Series, method: str = 'EWMA') -> pd.Series:
        """
        Calculates the Hull-White volatility scaling factors for historical simulation.
        Factor_i = sigma_current / sigma_i
        """
        if method.upper() == 'GARCH':
            var_series = VolatilityModeler.garch_variance(returns)
        else:
            var_series = VolatilityModeler.ewma_variance(returns)
            
        vol_series = np.sqrt(var_series)
        current_vol = vol_series.iloc[-1]
        
        # Scaling factor: ratio of today's volatility to historical day i's volatility
        scaling_factors = current_vol / vol_series
        return scaling_factors
