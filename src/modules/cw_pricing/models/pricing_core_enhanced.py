# -*- coding: utf-8 -*-
"""
🚀 ENHANCED PRICING MODELS - Research-Based Improvements
========================================================
Based on 2024-2025 research papers:
- Heston Stochastic Volatility Model (captures volatility smile)
- Machine Learning Pricing (Random Forest/XGBoost)
- Hybrid approach combining traditional + ML models

Research Sources:
- "Can Machine Learning Algorithms Outperform Traditional Models for Option Pricing?" (arXiv:2510.01446)
- "Machine learning for option pricing: an empirical investigation of network architectures" (arXiv:2307.07657)
- Heston Model implementation for stochastic volatility

Author: samvo
Version: 1.0 (Enhanced)
"""

import numpy as np
import pandas as pd
from scipy.stats import norm
from scipy.integrate import quad
from typing import Dict, Tuple, Any, Optional
import warnings
warnings.filterwarnings('ignore')

from src.modules.cw_pricing.models.pricing_core import RISK_FREE_RATE, calculate_d1_d2

# ==========================================
# 1. HESTON STOCHASTIC VOLATILITY MODEL
# ==========================================

def heston_characteristic_function(
    phi: float,
    S: float,
    K: float,
    T: float,
    r: float,
    kappa: float,
    theta: float,
    sigma: float,
    rho: float,
    v0: float
) -> complex:
    """
    Characteristic function for Heston model.
    
    Parameters:
    - phi: Integration variable
    - S: Current asset price
    - K: Strike price
    - T: Time to maturity
    - r: Risk-free rate
    - kappa: Mean reversion rate
    - theta: Long-term volatility
    - sigma: Volatility of volatility
    - rho: Correlation between asset and volatility
    - v0: Initial volatility
    """
    i = complex(0, 1)
    
    # Heston parameters
    d = np.sqrt((rho * sigma * i - kappa)**2 + (sigma**2) * (i + phi**2))
    g = (kappa - rho * sigma * i - d) / (kappa - rho * sigma * i + d)
    
    # Characteristic function
    C = (r * i * phi * T + (kappa * theta) / (sigma**2) * 
         ((kappa - rho * sigma * i - d) * T - 2 * np.log((1 - g * np.exp(-d * T)) / (1 - g))))
    
    D = ((kappa - rho * sigma * i - d) / (sigma**2) * 
         ((1 - np.exp(-d * T)) / (1 - g * np.exp(-d * T))))
    
    return np.exp(C + D * v0 + i * phi * np.log(S))

def heston_call_price(
    S: float,
    K: float,
    T: float,
    r: float,
    kappa: float = 2.0,
    theta: float = 0.05,
    sigma: float = 0.3,
    rho: float = -0.7,
    v0: float = 0.04
) -> float:
    """
    Calculate European call option price using Heston model.
    
    Parameters:
    - S: Current asset price
    - K: Strike price
    - T: Time to maturity (years)
    - r: Risk-free rate
    - kappa: Mean reversion rate (default: 2.0)
    - theta: Long-term volatility (default: 0.05)
    - sigma: Volatility of volatility (default: 0.3)
    - rho: Correlation (default: -0.7, typical for equities)
    - v0: Initial volatility (default: 0.04)
    """
    if T <= 0 or S <= 0 or K <= 0:
        return max(S - K, 0.0)
    
    i = complex(0, 1)
    
    # Integration for Heston model
    def integrand1(phi):
        return (np.exp(-i * phi * np.log(K)) * heston_characteristic_function(
            phi - i, S, K, T, r, kappa, theta, sigma, rho, v0) / (i * phi * S)).real
    
    def integrand2(phi):
        return (np.exp(-i * phi * np.log(K)) * heston_characteristic_function(
            phi, S, K, T, r, kappa, theta, sigma, rho, v0) / (i * phi)).real
    
    # Numerical integration
    P1, _ = quad(integrand1, 0, 100, limit=100)
    P2, _ = quad(integrand2, 0, 100, limit=100)
    
    call_price = S * (0.5 + P1 / np.pi) - np.exp(-r * T) * K * (0.5 + P2 / np.pi)
    return max(call_price, 0.0)

def heston_put_price(
    S: float,
    K: float,
    T: float,
    r: float,
    kappa: float = 2.0,
    theta: float = 0.05,
    sigma: float = 0.3,
    rho: float = -0.7,
    v0: float = 0.04
) -> float:
    """
    Calculate European put option price using Heston model (put-call parity).
    """
    call_price = heston_call_price(S, K, T, r, kappa, theta, sigma, rho, v0)
    put_price = call_price - S + np.exp(-r * T) * K
    return max(put_price, 0.0)

def heston_price(
    S: float,
    K: float,
    T: float,
    r: float,
    option_type: str = 'call',
    kappa: float = 2.0,
    theta: float = 0.05,
    sigma: float = 0.3,
    rho: float = -0.7,
    v0: float = 0.04
) -> float:
    """
    Wrapper for Heston price.
    """
    if option_type.lower() == 'call':
        return heston_call_price(S, K, T, r, kappa, theta, sigma, rho, v0)
    return heston_put_price(S, K, T, r, kappa, theta, sigma, rho, v0)

# ==========================================
# 1.5 HESTON AUTO-CALIBRATION
# ==========================================
def calibrate_heston(market_prices: np.ndarray, S: np.ndarray, K: np.ndarray, T: np.ndarray, r: float):
    """
    FINVISTA INSTITUTIONAL UPGRADE: Auto-Calibrate Heston Model to market prices.
    Uses Differential Evolution or L-BFGS-B to find optimal parameters.
    Returns: dict of optimal parameters.
    """
    from scipy.optimize import minimize

    # bounds for (kappa, theta, sigma, rho, v0)
    bounds = (
        (0.1, 10.0),    # kappa
        (0.01, 1.0),    # theta
        (0.01, 2.0),    # sigma
        (-0.99, 0.99),  # rho
        (0.01, 1.0)     # v0
    )
    
    # initial guess
    params_0 = [2.0, 0.05, 0.3, -0.7, 0.04]

    def objective(params):
        kappa, theta, sigma, rho, v0 = params
        error = 0.0
        
        # Feller condition penalty to ensure variance stays positive
        penalty = 0.0
        if 2 * kappa * theta <= sigma**2:
            penalty = 1e5
            
        for i in range(len(market_prices)):
            # If T is too small or price is bad, skip
            if T[i] < 0.01: continue
            
            p_model = heston_call_price(S[i], K[i], T[i], r, kappa, theta, sigma, rho, v0)
            error += (p_model - market_prices[i])**2
            
        return error + penalty

    res = minimize(objective, params_0, method='L-BFGS-B', bounds=bounds)
    
    opt_params = res.x
    return {
        "kappa": opt_params[0],
        "theta": opt_params[1],
        "sigma": opt_params[2],
        "rho": opt_params[3],
        "v0": opt_params[4],
        "success": res.success
    }
    """
    Unified Heston pricing function.
    """
    if option_type.lower() == 'call':
        return heston_call_price(S, K, T, r, kappa, theta, sigma, rho, v0)
    else:
        return heston_put_price(S, K, T, r, kappa, theta, sigma, rho, v0)

# ==========================================
# 2. MACHINE LEARNING PRICING MODEL
# ==========================================

class MLOptionPricer:
    """
    Machine Learning-based option pricing using ensemble methods.
    Based on research showing ML can outperform traditional models.
    """
    
    def __init__(self, model_type: str = 'random_forest'):
        """
        Initialize ML pricer.
        
        Parameters:
        - model_type: 'random_forest' or 'xgboost'
        """
        self.model_type = model_type
        self.model = None
        self.is_fitted = False
        
    def fit(self, X: pd.DataFrame, y: pd.Series):
        """
        Train the ML model on historical option data.
        
        Parameters:
        - X: Features [S, K, T, r, historical_volatility, volume, etc.]
        - y: Target option prices
        """
        try:
            if self.model_type == 'random_forest':
                from sklearn.ensemble import RandomForestRegressor
                self.model = RandomForestRegressor(
                    n_estimators=100,
                    max_depth=15,
                    min_samples_split=10,
                    random_state=42,
                    n_jobs=-1
                )
            elif self.model_type == 'xgboost':
                from xgboost import XGBRegressor
                self.model = XGBRegressor(
                    n_estimators=100,
                    max_depth=8,
                    learning_rate=0.1,
                    random_state=42,
                    n_jobs=-1
                )
            else:
                raise ValueError(f"Unknown model type: {self.model_type}")
            
            self.model.fit(X, y)
            self.is_fitted = True
            
        except ImportError as e:
            print(f"Warning: {e}. ML pricing not available.")
            self.is_fitted = False
    
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Predict option prices using trained model.
        """
        if not self.is_fitted or self.model is None:
            raise ValueError("Model not fitted. Call fit() first.")
        
        return self.model.predict(X)
    
    def get_feature_importance(self) -> Dict[str, float]:
        """
        Get feature importance from trained model.
        """
        if not self.is_fitted or self.model is None:
            return {}
        
        if hasattr(self.model, 'feature_importances_'):
            return dict(zip(self.model.feature_names_in_, self.model.feature_importances_))
        return {}

def create_ml_features(
    S: float,
    K: float,
    T: float,
    r: float,
    historical_volatility: float,
    volume: float = 0.0,
    underlying_return: float = 0.0,
    days_to_maturity: int = 0
) -> Dict[str, float]:
    """
    Create features for ML pricing model.
    Based on research showing these features improve ML pricing accuracy.
    """
    moneyness = S / K if K > 0 else 0
    log_moneyness = np.log(moneyness) if moneyness > 0 else 0
    
    return {
        'S': S,
        'K': K,
        'T': T,
        'r': r,
        'moneyness': moneyness,
        'log_moneyness': log_moneyness,
        'historical_volatility': historical_volatility,
        'volume': volume,
        'underlying_return': underlying_return,
        'days_to_maturity': days_to_maturity,
        'S_K_ratio': S / K if K > 0 else 0,
        'T_sqrt': np.sqrt(T) if T > 0 else 0
    }

# ==========================================
# 3. HYBRID PRICING MODEL (Traditional + ML)
# ==========================================

class HybridPricer:
    """
    Hybrid pricing model combining traditional models with ML corrections.
    Research shows this approach often outperforms individual models.
    """
    
    def __init__(self, ml_pricer: Optional[MLOptionPricer] = None):
        """
        Initialize hybrid pricer.
        
        Parameters:
        - ml_pricer: Trained ML pricer (optional)
        """
        self.ml_pricer = ml_pricer
        self.use_ml = ml_pricer is not None and ml_pricer.is_fitted
        
    def price(
        self,
        S: float,
        K: float,
        T: float,
        r: float,
        sigma: float,
        option_type: str = 'call',
        model: str = 'black_scholes',
        **kwargs
    ) -> float:
        """
        Price using hybrid approach.
        
        Parameters:
        - model: 'black_scholes', 'heston', or 'hybrid'
        - kwargs: Additional parameters for specific models
        """
        # Get traditional model price
        if model == 'heston':
            traditional_price = heston_price(S, K, T, r, option_type, **kwargs)
        else:
            # Black-Scholes (import from pricing_core)
            from src.modules.cw_pricing.models.pricing_core import calculate_d1_d2
            d1, d2 = calculate_d1_d2(S, K, T, r, sigma)
            if option_type.lower() == 'call':
                traditional_price = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
            else:
                traditional_price = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
        
        # Apply ML correction if available
        if self.use_ml and model == 'hybrid':
            features = create_ml_features(S, K, T, r, sigma, **kwargs)
            feature_df = pd.DataFrame([features])
            ml_price = self.ml_pricer.predict(feature_df)[0]
            
            # Weighted average (research suggests 70% traditional, 30% ML works well)
            hybrid_price = 0.7 * traditional_price + 0.3 * ml_price
            return max(hybrid_price, 0.0)
        
        return max(traditional_price, 0.0)

# ==========================================
# 4. MODEL COMPARISON & VALIDATION
# ==========================================

def compare_pricing_models(
    market_prices: pd.Series,
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    option_type: str = 'call'
) -> Dict[str, Dict[str, float]]:
    """
    Compare different pricing models against market prices.
    
    Returns metrics for each model:
    - MAE: Mean Absolute Error
    - RMSE: Root Mean Squared Error
    - MAPE: Mean Absolute Percentage Error
    """
    from src.modules.cw_pricing.models.pricing_core import calculate_d1_d2
    
    results = {}
    
    # Black-Scholes
    d1, d2 = calculate_d1_d2(S, K, T, r, sigma)
    if option_type.lower() == 'call':
        bs_price = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    else:
        bs_price = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
    
    bs_errors = market_prices - bs_price
    results['black_scholes'] = {
        'MAE': np.mean(np.abs(bs_errors)),
        'RMSE': np.sqrt(np.mean(bs_errors**2)),
        'MAPE': np.mean(np.abs(bs_errors / market_prices)) * 100
    }
    
    # Heston (with default parameters)
    heston_price_val = heston_price(S, K, T, r, option_type)
    heston_errors = market_prices - heston_price_val
    results['heston'] = {
        'MAE': np.mean(np.abs(heston_errors)),
        'RMSE': np.sqrt(np.mean(heston_errors**2)),
        'MAPE': np.mean(np.abs(heston_errors / market_prices)) * 100
    }
    
    return results

# ==========================================
# 5. CALIBRATION HELPERS
# ==========================================

def calibrate_heston_parameters(
    market_prices: pd.Series,
    S: float,
    K: float,
    T: float,
    r: float
) -> Dict[str, float]:
    """
    Calibrate Heston parameters to match market prices.
    Simple calibration using grid search (can be improved with optimization).
    
    Returns calibrated parameters: kappa, theta, sigma, rho, v0
    """
    from scipy.optimize import minimize
    
    def objective(params):
        kappa, theta, sigma, rho, v0 = params
        model_price = heston_price(S, K, T, r, 'call', kappa, theta, sigma, rho, v0)
        return (model_price - market_prices.mean())**2
    
    # Initial guess (typical values from research)
    initial_guess = [2.0, 0.05, 0.3, -0.7, 0.04]
    
    # Bounds
    bounds = [
        (0.1, 10.0),   # kappa
        (0.01, 0.5),   # theta
        (0.1, 1.0),    # sigma
        (-0.99, 0.99), # rho
        (0.01, 0.5)    # v0
    ]
    
    result = minimize(objective, initial_guess, bounds=bounds, method='L-BFGS-B')
    
    if result.success:
        kappa, theta, sigma, rho, v0 = result.x
        return {
            'kappa': kappa,
            'theta': theta,
            'sigma': sigma,
            'rho': rho,
            'v0': v0,
            'calibration_error': result.fun
        }
    else:
        # Return default values if calibration fails
        return {
            'kappa': 2.0,
            'theta': 0.05,
            'sigma': 0.3,
            'rho': -0.7,
            'v0': 0.04,
            'calibration_error': float('inf')
        }

# ==========================================
# USAGE EXAMPLE
# ==========================================

if __name__ == "__main__":
    print("=" * 80)
    print("ENHANCED PRICING MODELS - Research-Based Improvements")
    print("=" * 80)
    
    # Example parameters
    S = 100.0  # Underlying price
    K = 95.0   # Strike price
    T = 0.25   # 3 months
    r = 0.045  # Risk-free rate
    sigma = 0.3  # Volatility
    
    print(f"\nParameters: S={S}, K={K}, T={T}y, r={r}, σ={sigma}")
    
    # Black-Scholes price
    from src.modules.cw_pricing.models.pricing_core import calculate_d1_d2
    d1, d2 = calculate_d1_d2(S, K, T, r, sigma)
    bs_price = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    print(f"\nBlack-Scholes Price: {bs_price:.4f}")
    
    # Heston price
    heston_price_val = heston_price(S, K, T, r, 'call')
    print(f"Heston Price: {heston_price_val:.4f}")
    
    print("\n" + "=" * 80)
    print("Research findings suggest:")
    print("- Heston model captures volatility smile better than Black-Scholes")
    print("- ML models (Random Forest, XGBoost) can outperform traditional models")
    print("- Hybrid approach combining both often yields best results")
    print("=" * 80)
