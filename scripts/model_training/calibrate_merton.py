# -*- coding: utf-8 -*-
"""
🎯 FINVISTA: MERTON JUMP-DIFFUSION AUTO-CALIBRATION
==================================================
Runs Maximum Likelihood Estimation (MLE) to estimate Poisson jump intensity (lambda),
mean jump size (mu_J), and jump volatility (sigma_J) from historical stock returns.
Saves calibrated parameters to data/processed/merton_calibrated_params.json.

Author: samvo
"""

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import norm as scipy_norm
import math
import sys
import os
import json

# Ensure project root is on PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.database import SessionLocal, StockHistoricalPrice, CompanyDistressAnalysis
from src.core.utils import logger

def merton_log_likelihood(params, returns, dt=1/252):
    """
    Negative log-likelihood function for Merton Jump-Diffusion model.
    """
    mu, sigma, lamb, mu_J, sigma_J = params
    
    # Boundary constraints
    if sigma <= 0.001 or lamb <= 0.001 or sigma_J <= 0.001:
        return 1e15
        
    kappa = np.exp(mu_J + 0.5 * sigma_J**2) - 1
    drift = (mu - 0.5 * sigma**2 - lamb * kappa) * dt
    
    likelihood = 0.0
    # Truncate Poisson sum at n = 4 jumps per day (extremely rare to have >4 jumps/day)
    for n in range(5):
        # poisson probability P(N = n)
        poisson_prob = np.exp(-lamb * dt) * ((lamb * dt)**n) / math.factorial(n)
        mean = drift + n * mu_J
        variance = (sigma**2) * dt + n * (sigma_J**2)
        std = np.sqrt(variance)
        
        pdf_val = scipy_norm.pdf(returns, loc=mean, scale=std)
        likelihood += poisson_prob * pdf_val
        
    # Prevent log(0)
    log_lik = np.log(np.maximum(likelihood, 1e-15))
    return -np.sum(log_lik)

def calibrate_merton_mle(returns: np.ndarray) -> tuple:
    """
    Run MLE nonlinear optimization to estimate Merton parameters.
    Returns: (lamb, mu_J, sigma_J)
    """
    if len(returns) < 50:
        return 1.0, -0.05, 0.15 # Fallback defaults
        
    # Initial guesses based on sample moments
    initial_mu = np.mean(returns) * 252
    initial_sigma = np.std(returns) * np.sqrt(252)
    initial_lamb = 1.0
    initial_mu_J = -0.05
    initial_sigma_J = 0.15
    
    guess = [initial_mu, initial_sigma, initial_lamb, initial_mu_J, initial_sigma_J]
    
    bounds = [
        (-2.0, 2.0),       # mu
        (0.01, 1.5),       # sigma (diffusion vol)
        (0.05, 10.0),      # lambda (jump intensity per year)
        (-0.5, 0.5),       # mu_J (mean jump size)
        (0.01, 1.0)        # sigma_J (jump vol)
    ]
    
    try:
        res = minimize(merton_log_likelihood, guess, args=(returns,), method='L-BFGS-B', bounds=bounds)
        if res.success:
            _, _, lamb, mu_J, sigma_J = res.x
            return float(lamb), float(mu_J), float(sigma_J)
        else:
            # If not converged, try with differential evolution or fallback to simplex
            res_nm = minimize(merton_log_likelihood, guess, args=(returns,), method='Nelder-Mead')
            if res_nm.success:
                _, _, lamb, mu_J, sigma_J = res_nm.x
                # Check bounds manually
                lamb = max(0.05, min(10.0, lamb))
                mu_J = max(-0.5, min(0.5, mu_J))
                sigma_J = max(0.01, min(1.0, sigma_J))
                return float(lamb), float(mu_J), float(sigma_J)
    except Exception as e:
        logger.error(f"Error during optimization: {e}")
        
    return 1.0, -0.05, 0.15

def run_calibration():
    logger.info("🎯 Starting Merton Jump-Diffusion MLE calibration...")
    db = SessionLocal()
    
    try:
        # 1. Fetch unique tickers from stock history
        tickers = [r[0] for r in db.query(StockHistoricalPrice.symbol).distinct().all()]
        if not tickers:
            logger.warning("⚠️ No tickers found in stock_history database table.")
            return
            
        calibrated_params = {}
        
        # 2. Loop through each stock and calibrate
        for ticker in tickers:
            logger.info(f"📈 Processing {ticker}...")
            # Query last 5 years of daily data (approx. 1300 rows)
            prices = db.query(StockHistoricalPrice).filter(
                StockHistoricalPrice.symbol == ticker
            ).order_by(StockHistoricalPrice.date.desc()).limit(1300).all()
            
            if len(prices) < 50:
                logger.warning(f"   Skipping {ticker} (insufficient price history: {len(prices)} days)")
                continue
                
            # Sort chronological
            prices = sorted(prices, key=lambda x: x.date)
            close_prices = np.array([p.close for p in prices if p.close is not None and p.close > 0], dtype=float)
            
            if len(close_prices) < 50:
                continue
                
            # Compute daily log returns
            returns = np.diff(np.log(close_prices))
            
            # Run MLE Calibration
            lamb, mu_J, sigma_J = calibrate_merton_mle(returns)
            
            calibrated_params[ticker] = {
                "lamb": lamb,
                "mu_J": mu_J,
                "sigma_J": sigma_J,
                "calibrated_at": pd.Timestamp.now().isoformat()
            }
            logger.info(f"   Calibrated parameters: λ={lamb:.3f} | μ_J={mu_J:.2%} | σ_J={sigma_J:.2%}")
            
            # 3. Write back to distress analysis table if applicable for latest year
            latest_distress = db.query(CompanyDistressAnalysis).filter(
                CompanyDistressAnalysis.ticker == ticker
            ).order_by(CompanyDistressAnalysis.year.desc()).first()
            
            if latest_distress:
                # We can update the merton_dd or merton_pd if desired here
                # but to avoid database locking, we'll focus on parameter caching first
                pass
                
        # 4. Save results to JSON file
        out_dir = os.path.join("data", "processed")
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, "merton_calibrated_params.json")
        
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(calibrated_params, f, indent=4)
            
        logger.info(f"✅ Saved calibrated parameters for {len(calibrated_params)} tickers to {out_path}")
        
    finally:
        db.close()

if __name__ == "__main__":
    run_calibration()
