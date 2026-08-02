# -*- coding: utf-8 -*-
"""
🏆 FINVISTA: MERTON STRUCTURAL CREDIT RISK SOLVER
================================================
Calculates corporate credit risk parameters (Distance to Default, Probability of Default)
using Merton's (1974) structural model. Equity is modeled as a Call Option on total assets.

Author: samvo
"""

import numpy as np
from scipy.stats import norm
from scipy.optimize import fsolve
from typing import Tuple, Dict, Any

def merton_equations(vars_to_solve: np.ndarray, E: float, sigma_E: float, D: float, T: float, r: float, q: float = 0.0) -> np.ndarray:
    """
    System of non-linear equations for the Merton model:
    1) E - [ V * e^{-qT} * N(d1) - D * e^{-rT} * N(d2) ] = 0
    2) sigma_E * E - e^{-qT} * N(d1) * sigma_V * V = 0
    """
    V, sigma_V = vars_to_solve[0], vars_to_solve[1]
    
    # Boundary constraints to prevent negative or zero values in log/sqrt
    if V <= 1e-5 or sigma_V <= 1e-5:
        return np.array([V - 1e-5, sigma_V - 1e-5])
        
    sqrt_T = np.sqrt(T)
    d1 = (np.log(V / D) + (r - q + 0.5 * sigma_V ** 2) * T) / (sigma_V * sqrt_T)
    d2 = d1 - sigma_V * sqrt_T
    
    eq1 = V * np.exp(-q * T) * norm.cdf(d1) - D * np.exp(-r * T) * norm.cdf(d2) - E
    eq2 = np.exp(-q * T) * norm.cdf(d1) * sigma_V * V - sigma_E * E
    
    return np.array([eq1, eq2])

def solve_merton_model(
    equity_val: float, 
    equity_vol: float, 
    total_debt: float, 
    T: float = 1.0, 
    risk_free_rate: float = 0.045, 
    dividend_yield: float = 0.0
) -> Dict[str, float]:
    """
    Solves the Merton (1974) model to estimate corporate asset value and volatility.
    
    Parameters:
        equity_val: Market Capitalization of the company (E) in VND
        equity_vol: Historical equity volatility (sigma_E) as decimal (e.g. 0.35)
        total_debt: Book value of liabilities (D) in VND (Short-term Debt + 0.5 * Long-term Debt)
        T: Time horizon in years (default: 1.0 year)
        risk_free_rate: Risk-free rate (r) as decimal (default: 0.045)
        dividend_yield: Dividend yield (q) as decimal (default: 0.0)
        
    Returns:
        Dict containing:
            'asset_value': Solved Asset Value (V)
            'asset_volatility': Solved Asset Volatility (sigma_V)
            'distance_to_default': Distance to Default (DD)
            'default_probability': Probability of Default (PD)
    """
    # Safeguard inputs
    if equity_val <= 0 or total_debt <= 0:
        return {
            'asset_value': max(0.0, equity_val),
            'asset_volatility': equity_vol,
            'distance_to_default': 0.0,
            'default_probability': 1.0
        }
    if equity_vol <= 0:
        equity_vol = 0.01 # minimum floor

    # Initial Guesses (standard KMV approximation)
    V_init = equity_val + total_debt
    sigma_V_init = equity_vol * (equity_val / V_init)
    
    initial_guess = np.array([V_init, sigma_V_init])
    
    try:
        # Solve the system of equations
        solved_vars, info, ier, mesg = fsolve(
            merton_equations, 
            initial_guess, 
            args=(equity_val, equity_vol, total_debt, T, risk_free_rate, dividend_yield),
            full_output=True
        )
        
        V_sol, sigma_V_sol = solved_vars[0], solved_vars[1]
        
        # Check convergence and feasibility
        if ier != 1 or V_sol <= 0 or sigma_V_sol <= 0:
            # Fallback solver if fsolve failed to converge properly
            V_sol = V_init
            sigma_V_sol = max(0.01, sigma_V_init)
            
    except Exception:
        V_sol = V_init
        sigma_V_sol = max(0.01, sigma_V_init)

    # Calculate Distance to Default (DD) and Probability of Default (PD)
    sqrt_T = np.sqrt(T)
    # DD = d2 under risk-neutral/standard assumptions
    dd = (np.log(V_sol / total_debt) + (risk_free_rate - dividend_yield - 0.5 * sigma_V_sol ** 2) * T) / (sigma_V_sol * sqrt_T)
    pd = float(norm.cdf(-dd))
    
    # Clip extreme values for PD
    pd = max(0.0, min(pd, 1.0))
    
    return {
        'asset_value': float(V_sol),
        'asset_volatility': float(sigma_V_sol),
        'distance_to_default': float(dd),
        'default_probability': pd
    }
