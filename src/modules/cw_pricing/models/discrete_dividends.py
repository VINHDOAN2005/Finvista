# -*- coding: utf-8 -*-
"""
🏆 FINVISTA QUANT PRO: DISCRETE DIVIDEND PRICING ENGINE
======================================================
Provides quantitative pricing models adjusted for discrete cash dividends.
Vietnamese underlying stocks often pay large lump-sum cash dividends.

Models implemented:
  1. Present Value Adjustment: S* = S - sum(D_i * e^(-r * t_i))
  2. Cox-Ross-Rubinstein (CRR) Binomial Tree with discrete dividends.

Author: samvo
"""

import math
import numpy as np
from typing import List, Tuple, Dict, Any

def calculate_dividend_adjusted_spot(S: float, r: float, dividends: List[Tuple[float, float]], T: float) -> float:
    """
    Subtracts the present value of all dividends paid during the life of the warrant
    from the spot price of the underlying asset.
    
    Args:
        S: Current stock price (spot)
        r: Risk-free rate (continuous decimal)
        dividends: List of tuples (dividend_amount, time_to_pay_in_years)
        T: Time to maturity of the warrant (in years)
        
    Returns:
        Dividend-adjusted stock price S*
    """
    pv_dividends = 0.0
    for div_amount, div_time in dividends:
        if 0.0 < div_time < T:
            pv_dividends += div_amount * math.exp(-r * div_time)
            
    adjusted_S = S - pv_dividends
    return max(adjusted_S, 1e-4)

def binomial_tree_dividend_adjusted(S: float, K: float, T: float, r: float, sigma: float, 
                                    dividends: List[Tuple[float, float]], steps: int = 100, 
                                    option_type_is_call: bool = True, is_american: bool = False) -> float:
    """
    CRR Binomial Tree model adjusted for discrete dividends.
    Escapes the non-recombining tree problem by splitting the stock price
    into a risky component and a riskless (dividend-backing) component.
    
    Args:
        S: Spot stock price
        K: Strike price
        T: Time to maturity (years)
        r: Risk-free rate (continuous decimal)
        sigma: Volatility (decimal)
        dividends: List of tuples (dividend_amount, time_to_pay_in_years)
        steps: Number of steps in binomial tree
        option_type_is_call: True for Call, False for Put
        is_american: True for American option, False for European
        
    Returns:
        Theoretical option price
    """
    if T <= 0 or S <= 0 or K <= 0 or sigma <= 0:
        return max(S - K, 0.0) if option_type_is_call else max(K - S, 0.0)
        
    dt = T / steps
    u = math.exp(sigma * math.sqrt(dt))
    d = 1.0 / u
    p = (math.exp(r * dt) - d) / (u - d)
    
    # Check if p is valid
    if p <= 0 or p >= 1:
        # Fallback to standard risk-neutral probability adjustment
        p = 0.5
        
    discount = math.exp(-r * dt)
    
    # Calculate the present value of dividends at time = 0
    pv_div = sum(amount * math.exp(-r * time) for amount, time in dividends if 0.0 < time < T)
    S_star = S - pv_div
    
    if S_star <= 0:
        S_star = S * 0.01 # Fallback to prevent negative spot
        
    # Construct the binomial tree for the S_star (risky component)
    S_nodes = np.zeros(steps + 1)
    for j in range(steps + 1):
        S_nodes[j] = S_star * (u**(steps - j)) * (d**j)
        
    # Option values at maturity (T)
    # Add back the dividend component (at T, dividend component is 0)
    option_values = np.zeros(steps + 1)
    for j in range(steps + 1):
        spot_at_T = S_nodes[j] # Dividends have all been paid by T
        if option_type_is_call:
            option_values[j] = max(spot_at_T - K, 0.0)
        else:
            option_values[j] = max(K - spot_at_T, 0.0)
            
    # Backwards induction
    for i in range(steps - 1, -1, -1):
        t_current = i * dt
        # Calculate PV of remaining dividends at this step's time
        pv_remaining = sum(amount * math.exp(-r * (div_time - t_current)) 
                            for amount, div_time in dividends if t_current < div_time < T)
        
        for j in range(i + 1):
            # Risky component at step i
            S_risky = S_star * (u**(i - j)) * (d**j)
            spot_current = S_risky + pv_remaining
            
            # Continuation value
            val = (p * option_values[j] + (1.0 - p) * option_values[j + 1]) * discount
            
            if is_american:
                # Early exercise check
                if option_type_is_call:
                    exercise = max(spot_current - K, 0.0)
                else:
                    exercise = max(K - spot_current, 0.0)
                option_values[j] = max(val, exercise)
            else:
                option_values[j] = val
                
    return float(option_values[0])
