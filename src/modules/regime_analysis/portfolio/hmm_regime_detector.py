# -*- coding: utf-8 -*-
"""
🏆 FINVISTA: HMM REGIME DETECTION MODULE
=========================================
Integrates Hidden Markov Model regime detection from regime-switching-portfolio
to learn market regimes from real Vietnamese stock data instead of using mock data.

Author: samvo
"""

import numpy as np
import pandas as pd
import os
import sys
import warnings
from hmmlearn.hmm import GaussianHMM

# Add regime-switching-portfolio to path for reference
REGIME_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'regime-switching-portfolio')
if REGIME_DIR not in sys.path:
    sys.path.insert(0, REGIME_DIR)


def fit_hmm(returns: pd.DataFrame, n_states: int = 3, random_state: int = 42) -> GaussianHMM:
    """
    Fit Hidden Markov Model to returns data.
    
    Args:
        returns: DataFrame of asset returns (T x N)
        n_states: Number of regime states
        random_state: Random seed for reproducibility
    
    Returns:
        Fitted GaussianHMM model
    """
    x = np.asarray(returns.values, dtype=float)
    model = GaussianHMM(
        n_components=n_states,
        covariance_type="diag",
        n_iter=500,
        tol=1e-4,
        random_state=random_state,
        verbose=False,
        init_params="mcs",
        params="mcs",
    )
    
    # Suppress HMM output during fitting
    devnull = open(os.devnull, "w")
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = devnull
    sys.stderr = devnull
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model.fit(x)
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        devnull.close()
    return model


def is_valid_model(model: GaussianHMM) -> bool:
    """Check if HMM model is valid (finite probabilities, valid transitions)."""
    sp = model.startprob_
    tm = model.transmat_
    if not np.isfinite(sp).all():
        return False
    if not np.isfinite(tm).all():
        return False
    if abs(sp.sum() - 1.0) > 0.01:
        return False
    if not (tm.sum(axis=1) > 0.5).all():
        return False
    return True


def posterior_probs(model: GaussianHMM, returns: pd.DataFrame) -> pd.DataFrame:
    """
    Compute posterior regime probabilities for each timestep.
    
    Args:
        model: Fitted HMM model
        returns: DataFrame of returns (T x N)
    
    Returns:
        DataFrame of regime probabilities (T x K)
    """
    x = np.asarray(returns.values, dtype=float)
    _, post = model.score_samples(x)
    return pd.DataFrame(post, index=returns.index, columns=[f"state_{i}" for i in range(model.n_components)])


def viterbi_path(model: GaussianHMM, returns: pd.DataFrame) -> pd.Series:
    """
    Compute most likely regime path using Viterbi algorithm.
    
    Args:
        model: Fitted HMM model
        returns: DataFrame of returns (T x N)
    
    Returns:
        Series of regime labels (T)
    """
    x = np.asarray(returns.values, dtype=float)
    states = model.predict(x)
    return pd.Series(states, index=returns.index, name="state")


def regime_stats_by_label(returns: pd.DataFrame, labels: pd.Series) -> dict:
    """
    Compute mean and covariance statistics per regime.
    
    Args:
        returns: DataFrame of returns (T x N)
        labels: Series of regime labels (T)
    
    Returns:
        Dictionary mapping regime_id -> {"mu": mean vector, "cov": covariance matrix}
    """
    stats = {}
    for k in np.unique(labels.values):
        mask = (labels.values == k)
        r = returns.iloc[mask]
        mu = r.mean()
        cov = r.cov()
        stats[int(k)] = {"mu": mu, "cov": cov}
    return stats


def detect_regimes_from_db(symbols: list, start_date: str = None, end_date: str = None, 
                           n_states: int = 3, random_state: int = 42) -> tuple:
    """
    Load stock data from Finvista database and detect regimes using HMM.
    
    Args:
        symbols: List of stock symbols to analyze
        start_date: Start date (YYYY-MM-DD), defaults to 1 year ago
        end_date: End date (YYYY-MM-DD), defaults to today
        n_states: Number of regime states
        random_state: Random seed
    
    Returns:
        Tuple of (returns_df, regime_probs, regime_labels, regime_stats, model)
    """
    from datetime import datetime, timedelta
    from src.core.database import engine
    import pandas as pd
    
    # Default date range: last 2 years
    if end_date is None:
        end_date = datetime.now().strftime('%Y-%m-%d')
    if start_date is None:
        start_date = (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d')
    
    # Load stock data from database
    query = f"""
        SELECT symbol, date, close
        FROM stock_history
        WHERE symbol IN ({','.join([f"'{s}'" for s in symbols])})
        AND date >= '{start_date}' AND date <= '{end_date}'
        ORDER BY symbol, date
    """
    
    try:
        df = pd.read_sql(query, engine)
    except Exception as e:
        print(f"❌ Error loading data from database: {e}")
        return None, None, None, None, None
    
    if df.empty:
        print(f"❌ No data found for symbols {symbols} in date range {start_date} to {end_date}")
        return None, None, None, None, None
    
    # Pivot to wide format (date x symbol)
    df_pivot = df.pivot(index='date', columns='symbol', values='close')
    df_pivot.index = pd.to_datetime(df_pivot.index)
    df_pivot = df_pivot.sort_index()
    
    # Forward fill missing values
    df_pivot = df_pivot.fillna(method='ffill').fillna(method='bfill')
    
    # Compute log returns
    returns = np.log(df_pivot / df_pivot.shift(1)).dropna()
    
    # Fit HMM
    model = fit_hmm(returns, n_states=n_states, random_state=random_state)
    
    if not is_valid_model(model):
        print("❌ HMM model validation failed")
        return None, None, None, None, None
    
    # Compute regime probabilities and labels
    probs = posterior_probs(model, returns)
    labels = viterbi_path(model, returns)
    stats = regime_stats_by_label(returns, labels)
    
    print(f"✅ HMM regime detection completed for {len(symbols)} symbols")
    print(f"   Regimes detected: {n_states}")
    print(f"   Date range: {returns.index[0].strftime('%Y-%m-%d')} to {returns.index[-1].strftime('%Y-%m-%d')}")
    print(f"   Total observations: {len(returns)}")
    
    # Print regime statistics
    for k, stat in stats.items():
        print(f"\n   Regime {k}:")
        print(f"     Mean annualized returns: {(stat['mu'] * 252 * 100).round(2)}%")
        print(f"     Annualized volatility: {(np.sqrt(np.diag(stat['cov'])) * np.sqrt(252) * 100).round(2)}%")
    
    return returns, probs, labels, stats, model


def detect_regimes_from_csv(csv_path: str, symbols: list = None, 
                            n_states: int = 3, random_state: int = 42) -> tuple:
    """
    Load stock data from CSV file and detect regimes using HMM.
    
    Args:
        csv_path: Path to CSV file with stock price data
        symbols: List of symbols to use (if None, use all available)
        n_states: Number of regime states
        random_state: Random seed
    
    Returns:
        Tuple of (returns_df, regime_probs, regime_labels, regime_stats, model)
    """
    df = pd.read_csv(csv_path)
    
    # Ensure date column exists
    if 'date' not in df.columns:
        print("❌ CSV must have 'date' column")
        return None, None, None, None, None
    
    # Filter symbols if specified
    if symbols is not None:
        df = df[df['symbol'].isin(symbols)]
    
    # Pivot to wide format
    df_pivot = df.pivot(index='date', columns='symbol', values='close')
    df_pivot.index = pd.to_datetime(df_pivot.index)
    df_pivot = df_pivot.sort_index()
    
    # Forward fill missing values
    df_pivot = df_pivot.fillna(method='ffill').fillna(method='bfill')
    
    # Compute log returns
    returns = np.log(df_pivot / df_pivot.shift(1)).dropna()
    
    # Fit HMM
    model = fit_hmm(returns, n_states=n_states, random_state=random_state)
    
    if not is_valid_model(model):
        print("❌ HMM model validation failed")
        return None, None, None, None, None
    
    # Compute regime probabilities and labels
    probs = posterior_probs(model, returns)
    labels = viterbi_path(model, returns)
    stats = regime_stats_by_label(returns, labels)
    
    print(f"✅ HMM regime detection completed from CSV")
    print(f"   Regimes detected: {n_states}")
    print(f"   Total observations: {len(returns)}")
    
    return returns, probs, labels, stats, model


if __name__ == "__main__":
    # Test with VN30 blue-chip stocks
    vn30_stocks = ['VCB', 'VIC', 'VHM', 'HPG', 'FPT', 'MSN', 'MWG', 'ACB']
    
    print("=" * 80)
    print(" 🧪 TESTING HMM REGIME DETECTION ON VN STOCKS")
    print("=" * 80)
    
    # Try loading from database first
    returns, probs, labels, stats, model = detect_regimes_from_db(
        symbols=vn30_stocks,
        n_states=3,
        random_state=42
    )
    
    if returns is None:
        # Fallback to CSV if database fails
        csv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 
                                'data', 'processed', 'all_stock_historical_prices.csv')
        if os.path.exists(csv_path):
            print("📂 Falling back to CSV data source...")
            returns, probs, labels, stats, model = detect_regimes_from_csv(
                csv_path=csv_path,
                symbols=vn30_stocks,
                n_states=3,
                random_state=42
            )
    
    if returns is not None:
        # Save results
        output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
                                   'data', 'processed')
        os.makedirs(output_dir, exist_ok=True)
        
        probs.to_csv(os.path.join(output_dir, 'hmm_regime_probs.csv'))
        labels.to_csv(os.path.join(output_dir, 'hmm_regime_labels.csv'))
        returns.to_csv(os.path.join(output_dir, 'hmm_returns.csv'))
        
        print(f"\n💾 Results saved to {output_dir}")
        print("=" * 80)
