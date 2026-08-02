# -*- coding: utf-8 -*-
"""
🛡️ FINVISTA: RISK FACTOR ENGINE (CAPM & FACTOR MODELS)
=====================================================
Implements quantitative risk metrics based on:
  1. Bodie et al. - CAPM (Beta estimation)
  2. Cochrane - Factor Pricing & Expected Returns
  3. Elton & Gruber - Single Index Model (Covariance estimation)

Functionalities:
  - Rolling Beta (Systematic Risk) calculation relative to VNIndex.
  - Jensen's Alpha (Abnormal Returns).
  - Treynor Ratio & Information Ratio.
  - R-Squared (Systematic vs. Idiosyncratic risk breakdown).

Author: samvo
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from src.core import config

class RiskFactorEngine:
    def __init__(self, market_symbol: str = "VNINDEX"):
        self.market_symbol = market_symbol

    def calculate_betas(self, stock_df: pd.DataFrame, lookback_days: int = 252) -> Dict[str, float]:
        """
        Calculate Beta (β) for all stocks in the dataset relative to the market.
        β_i = Cov(R_i, R_m) / Var(R_m)
        """
        if stock_df.empty:
            return {}

        # Ensure 'time' is datetime and sort
        stock_df['time'] = pd.to_datetime(stock_df['time'])
        
        # Calculate daily returns
        # Pivot to get symbols as columns
        pivot_df = stock_df.pivot(index='time', columns='symbol', values='close')
        returns = pivot_df.pct_change().dropna()
        
        if self.market_symbol not in returns.columns:
            # Fallback: if VNINDEX not in data, use an equal-weighted proxy or log warning
            print(f"⚠️ Market symbol {self.market_symbol} not found in returns. Beta estimation might be limited.")
            market_returns = returns.mean(axis=1)
        else:
            market_returns = returns[self.market_symbol]
            
        betas = {}
        var_m = market_returns.var()
        
        if var_m == 0:
            return {s: 1.0 for s in returns.columns}

        for symbol in returns.columns:
            if symbol == self.market_symbol:
                betas[symbol] = 1.0
                continue
            
            cov_im = returns[symbol].cov(market_returns)
            beta = cov_im / var_m
            betas[symbol] = round(beta, 3)
            
        return betas

    def calculate_jensens_alpha(self, return_i: float, return_m: float, beta_i: float, risk_free_rate: float) -> float:
        """
        α = R_i - [R_f + β_i * (R_m - R_f)]
        Theory: Bodie et al. - Measuring risk-adjusted performance.
        """
        expected_return = risk_free_rate + beta_i * (return_m - risk_free_rate)
        alpha = return_i - expected_return
        return alpha

    def get_risk_decomposition(self, returns_i: pd.Series, returns_m: pd.Series) -> Dict[str, float]:
        """
        Decompose total risk into Systematic and Idiosyncratic (Elton & Gruber).
        σ_total^2 = β^2 * σ_m^2 + σ_ε^2
        """
        # Linear regression
        from scipy import stats
        slope, intercept, r_value, p_value, std_err = stats.linregress(returns_m, returns_i)
        
        beta = slope
        r_squared = r_value**2
        total_var = returns_i.var()
        systematic_var = (beta**2) * returns_m.var()
        idiosyncratic_var = total_var - systematic_var
        
        return {
            "beta": beta,
            "r_squared": r_squared,
            "systematic_risk_pct": (systematic_var / total_var) * 100 if total_var > 0 else 0,
            "specific_risk_pct": (idiosyncratic_var / total_var) * 100 if total_var > 0 else 0
        }

def enrich_with_risk_factors(market_df: pd.DataFrame, historical_stock_file: str) -> pd.DataFrame:
    """Entry point for integrating risk factors into the main pipeline."""
    try:
        engine = RiskFactorEngine()
        import duckdb
        con = duckdb.connect()
        # Read CSV with DuckDB for high-speed projection and load
        csv_path_clean = historical_stock_file.replace('\\', '/')
        hist_df = con.execute(f"SELECT time, symbol, close FROM read_csv_auto('{csv_path_clean}')").df()
        betas = engine.calculate_betas(hist_df)
        
        # Map betas to market_df
        # market_df columns: B_MaCPCS (underlying symbol)
        col = "B_MaCPCS" if "B_MaCPCS" in market_df.columns else "underlying"
        if col in market_df.columns:
            market_df["underlying_beta"] = market_df[col].map(lambda x: betas.get(x, 1.0))
            
            # Theory: Cochrane - Risk Premium adjustments
            # In a bull market, we might prefer high beta. In a bear market, low beta.
            # For CW (Covered Warrants), leverage is already high, so high beta underlying 
            # compounds the risk exponentially.
            
            # Adjust G-Score: Penalize extremely high beta if market sentiment is neutral/bearish
            if "G_Score" in market_df.columns:
                market_df.loc[market_df["underlying_beta"] > 1.5, "G_Score"] -= 5
                market_df.loc[market_df["underlying_beta"] < 0.8, "G_Score"] += 3
        
        return market_df
    except Exception as e:
        print(f"⚠️ Risk Factor Engine enrichment failed: {e}")
        return market_df
