# -*- coding: utf-8 -*-
"""
🏆 FINVISTA: KALMAN FILTER PRICE/RETURN DENOISER
===============================================
A simple 1D Kalman filter to smooth noisy returns or price series.

Author: samvo
"""

class KalmanFilterPrice:
    def __init__(self, process_variance: float = 1e-6, measurement_variance: float = 1e-4):
        self.process_variance = process_variance
        self.measurement_variance = measurement_variance
        self.post_estimate = 0.0
        self.post_error_covariance = 1.0
        self.is_initialized = False

    def reset(self):
        """Resets the Kalman Filter state."""
        self.post_estimate = 0.0
        self.post_error_covariance = 1.0
        self.is_initialized = False

    def update(self, measurement: float) -> float:
        """Updates the filter with a new measurement and returns the filtered estimate."""
        if not self.is_initialized:
            self.post_estimate = measurement
            self.post_error_covariance = 1.0
            self.is_initialized = True
            return self.post_estimate

        # Prediction step
        prior_estimate = self.post_estimate
        prior_error_covariance = self.post_error_covariance + self.process_variance

        # Measurement update step
        kalman_gain = prior_error_covariance / (prior_error_covariance + self.measurement_variance)
        self.post_estimate = prior_estimate + kalman_gain * (measurement - prior_estimate)
        self.post_error_covariance = (1.0 - kalman_gain) * prior_error_covariance

        return self.post_estimate


class KalmanFilter:
    def __init__(self, process_variance: float = 1e-6, measurement_variance: float = 1e-4):
        self.process_variance = process_variance
        self.measurement_variance = measurement_variance

    def estimate(self, ticker: str, days: int = 252) -> dict:
        ticker = ticker.upper().strip()
        import pandas as pd
        import numpy as np
        from src.core.database import engine
        
        query = f"SELECT date, close FROM stock_history WHERE symbol = '{ticker}' ORDER BY date ASC"
        try:
            df = pd.read_sql(query, engine)
        except Exception:
            df = pd.DataFrame()
            
        if df.empty:
            query = f"SELECT date, close FROM cw_history WHERE symbol = '{ticker}' ORDER BY date ASC"
            try:
                df = pd.read_sql(query, engine)
            except Exception:
                df = pd.DataFrame()
                
        if df.empty or len(df) < 5:
            return {
                "signal": "NEUTRAL",
                "latest_price": 0.0,
                "filtered_price": 0.0,
                "trend": "NEUTRAL",
                "error": "Insufficient data"
            }
            
        closes = df["close"].values
        
        kf_price = KalmanFilterPrice(self.process_variance, self.measurement_variance)
        filtered_prices = []
        for price in closes:
            filtered_prices.append(kf_price.update(price))
            
        latest_price = float(closes[-1])
        latest_filtered = float(filtered_prices[-1])
        prev_filtered = float(filtered_prices[-2]) if len(filtered_prices) > 1 else latest_filtered
        
        change = (latest_filtered - prev_filtered) / prev_filtered if prev_filtered != 0 else 0.0
        
        # Determine signal based on percentage change of the smoothed price
        if change > 0.00005:
            signal = "BULLISH"
        elif change < -0.00005:
            signal = "BEARISH"
        else:
            signal = "NEUTRAL"
            
        return {
            "signal": signal,
            "latest_price": latest_price,
            "filtered_price": latest_filtered,
            "trend": signal
        }

