# -*- coding: utf-8 -*-
"""
🏆 FINVISTA QUANT PRO: SABR IMPLIED VOLATILITY SURFACE MODEL
===========================================================
Implements the SABR model (Hagan et al., 2002) for modeling the Implied Volatility Smile
and constructing the 3D Volatility Surface for Covered Warrants.

Theoretical Parameters:
  * alpha: Initial volatility (vol of vol scale)
  * beta: Elasticity parameter (typically fixed, e.g., 0.5 for equities/CWs)
  * rho: Correlation between asset price and volatility
  * nu: Volatility of volatility (vol of vol)

Author: samvo
"""

import math
import numpy as np
from scipy.optimize import minimize
from typing import Tuple, List, Dict, Any

def sabr_implied_vol(F: float, K: float, T: float, alpha: float, beta: float, rho: float, nu: float) -> float:
    """
    Computes the Implied Volatility under the SABR model using Hagan's asymptotic formula.
    
    Args:
        F: Forward price of underlying asset
        K: Strike price of option/warrant
        T: Time to maturity (in years)
        alpha: Alpha parameter (volatility level)
        beta: Beta parameter (elasticity)
        rho: Rho parameter (correlation)
        nu: Nu parameter (vol of vol)
        
    Returns:
        Implied volatility (standard BSM input decimal, e.g., 0.35 for 35%)
    """
    # Defensive inputs
    F = max(F, 1e-6)
    K = max(K, 1e-6)
    T = max(T, 1e-4)
    alpha = max(alpha, 1e-4)
    nu = max(nu, 1e-4)
    rho = max(-0.999, min(0.999, rho))
    
    # Check if ATM
    if abs(F - K) < 1e-5:
        # ATM formula
        f_beta = F**(1.0 - beta)
        num = alpha / f_beta
        term1 = ((1.0 - beta)**2 / 24.0) * (alpha**2 / (F**(2.0 * (1.0 - beta))))
        term2 = 0.25 * (rho * beta * nu * alpha / f_beta)
        term3 = ((2.0 - 3.0 * rho**2) / 24.0) * nu**2
        vol = num * (1.0 + (term1 + term2 + term3) * T)
        return float(vol)
    
    # Non-ATM formula
    log_FK = math.log(F / K)
    one_minus_beta = 1.0 - beta
    
    fk_power = (F * K)**(one_minus_beta / 2.0)
    z = (nu / alpha) * fk_power * log_FK
    
    # Calculate x(z)
    val = (math.sqrt(1.0 - 2.0 * rho * z + z**2) + z - rho) / (1.0 - rho)
    if val <= 0:
        x_z = z # Fallback
    else:
        x_z = math.log(val)
        
    # Scale factor z / x(z)
    if abs(z) < 1e-5:
        z_over_xz = 1.0
    else:
        z_over_xz = z / x_z
        
    # Denominator components
    denom_term1 = 1.0 + (one_minus_beta**2 / 24.0) * log_FK**2 + (one_minus_beta**4 / 1920.0) * log_FK**4
    denom = fk_power * denom_term1
    
    # Time adjustment components
    time_term1 = (one_minus_beta**2 / 24.0) * (alpha**2 / (F * K)**one_minus_beta)
    time_term2 = 0.25 * (rho * beta * nu * alpha) / fk_power
    time_term3 = ((2.0 - 3.0 * rho**2) / 24.0) * nu**2
    time_adj = 1.0 + (time_term1 + time_term2 + time_term3) * T
    
    vol = (alpha / denom) * z_over_xz * time_adj
    return float(max(vol, 1e-4))

def calibrate_sabr(F: float, T: float, strikes: List[float], market_vols: List[float], beta: float = 0.5) -> Tuple[float, float, float]:
    """
    Calibrates the SABR model parameters (alpha, rho, nu) to fit a set of market implied volatilities.
    Beta is typically fixed beforehand (0.5 for equities/CWs is the market standard).
    
    Args:
        F: Forward price
        T: Time to maturity
        strikes: List of option strike prices
        market_vols: List of market implied volatilities (decimals)
        beta: Fixed beta parameter (default 0.5)
        
    Returns:
        Tuple of (alpha, rho, nu)
    """
    # Initial guesses
    # ATM Volatility approximation for alpha initial guess
    atm_vol = market_vols[0]
    for s, v in zip(strikes, market_vols):
        if abs(s - F) < abs(F * 0.05):
            atm_vol = v
            break
            
    alpha_guess = atm_vol * (F**(1.0 - beta))
    rho_guess = -0.30
    nu_guess = 0.40
    
    initial_params = [alpha_guess, rho_guess, nu_guess]
    bounds = [
        (1e-4, 5.0),       # alpha bounds
        (-0.99, 0.99),     # rho bounds
        (1e-4, 5.0)        # nu bounds
    ]
    
    def loss_function(params):
        alpha, rho, nu = params
        total_sq_err = 0.0
        for K, mkt_vol in zip(strikes, market_vols):
            model_vol = sabr_implied_vol(F, K, T, alpha, beta, rho, nu)
            total_sq_err += (model_vol - mkt_vol)**2
        return total_sq_err
        
    res = minimize(loss_function, initial_params, method='L-BFGS-B', bounds=bounds)
    
    if res.success:
        return float(res.x[0]), float(res.x[1]), float(res.x[2])
    return alpha_guess, rho_guess, nu_guess

class SabrVolatilitySurface:
    """Class to manage, calibrate and query the SABR Implied Volatility Surface."""
    def __init__(self, beta: float = 0.5):
        self.beta = beta
        self.calibrated_params = {} # (symbol, expiry_T) -> (alpha, rho, nu)
        
    def add_slice(self, symbol: str, F: float, T: float, strikes: List[float], market_vols: List[float]):
        """Calibrates and stores SABR parameters for a specific ticker and expiration."""
        alpha, rho, nu = calibrate_sabr(F, T, strikes, market_vols, self.beta)
        self.calibrated_params[(symbol, round(T, 4))] = {
            'alpha': alpha,
            'rho': rho,
            'nu': nu,
            'F': F
        }
        
    def get_vol(self, symbol: str, F: float, K: float, T: float, fallback_vol: float = 0.45) -> float:
        """Queries the SABR volatility surface for a specific strike and maturity."""
        # Find the closest maturity slice
        slices = [key for key in self.calibrated_params.keys() if key[0] == symbol]
        if not slices:
            return fallback_vol
            
        # Get the slice with the closest T
        closest_key = min(slices, key=lambda x: abs(x[1] - T))
        params = self.calibrated_params[closest_key]
        
        return sabr_implied_vol(
            F=F, 
            K=K, 
            T=T, 
            alpha=params['alpha'], 
            beta=self.beta, 
            rho=params['rho'], 
            nu=params['nu']
        )
