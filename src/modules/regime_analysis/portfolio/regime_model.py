from __future__ import annotations
import os
import sys
import warnings
import numpy as np
import pandas as pd
from hmmlearn.hmm import GaussianHMM


def align_states(model: GaussianHMM) -> GaussianHMM:
    """Sort the states of GaussianHMM by average volatility in ascending order.
    State 0 will be the lowest volatility (usually Bull), and the last state will be the highest volatility (Bear).
    """
    if not hasattr(model, "_covars_"):
        return model
    
    # Calculate average variance/volatility for each state
    if model.covariance_type == "diag":
        state_vols = np.mean(model._covars_, axis=1)
    elif model.covariance_type == "full":
        state_vols = np.array([np.trace(cov) for cov in model._covars_])
    else:
        state_vols = np.arange(model.n_components)
    
    idx_sort = np.argsort(state_vols)
    
    # Permute parameters using internal raw attributes to bypass setter validation issues
    model.means_ = model.means_[idx_sort]
    model._covars_ = model._covars_[idx_sort]
    model.startprob_ = model.startprob_[idx_sort]
    model.transmat_ = model.transmat_[np.ix_(idx_sort, idx_sort)]
    
    return model


def fit_hmm(returns: pd.DataFrame, n_states: int = 3, covariance_type: str = "full", random_state: int = 42) -> GaussianHMM:
    x = np.asarray(returns.values, dtype=float)
    model = GaussianHMM(
        n_components=n_states,
        covariance_type=covariance_type,
        n_iter=500,
        tol=1e-4,
        random_state=random_state,
        verbose=False,
        init_params="mcs",
        params="mcs",
    )
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
    
    # Align states by volatility to prevent state swapping in rolling windows
    if is_valid_model(model):
        model = align_states(model)
        
    return model


def is_valid_model(model: GaussianHMM) -> bool:
    if not hasattr(model, "startprob_") or model.startprob_ is None:
        return False
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
    x = np.asarray(returns.values, dtype=float)
    _, post = model.score_samples(x)
    return pd.DataFrame(post, index=returns.index, columns=[f"state_{i}" for i in range(model.n_components)])


def viterbi_path(model: GaussianHMM, returns: pd.DataFrame) -> pd.Series:
    x = np.asarray(returns.values, dtype=float)
    states = model.predict(x)
    return pd.Series(states, index=returns.index, name="state")


def regime_stats_by_label(returns: pd.DataFrame, labels: pd.Series):
    stats = {}
    for k in np.unique(labels.values):
        mask = (labels.values == k)
        r = returns.iloc[mask]
        mu = r.mean()
        cov = r.cov()
        stats[int(k)] = {"mu": mu, "cov": cov, "returns": r}
    return stats


def compute_bic(model: GaussianHMM, returns: pd.DataFrame) -> float:
    """Calculates Bayesian Information Criterion (BIC) for the HMM."""
    x = np.asarray(returns.values, dtype=float)
    log_likelihood = model.score(x)
    n_features = returns.shape[1]
    n_states = model.n_components
    n_params = n_states * (n_states - 1) + (n_states - 1) + n_states * n_features
    if model.covariance_type == "diag":
        n_params += n_states * n_features
    elif model.covariance_type == "full":
        n_params += n_states * n_features * (n_features + 1) // 2
    
    n_samples = x.shape[0]
    return -2.0 * log_likelihood + n_params * np.log(n_samples)


def compute_aic(model: GaussianHMM, returns: pd.DataFrame) -> float:
    """Calculates Akaike Information Criterion (AIC) for the HMM."""
    x = np.asarray(returns.values, dtype=float)
    log_likelihood = model.score(x)
    n_features = returns.shape[1]
    n_states = model.n_components
    n_params = n_states * (n_states - 1) + (n_states - 1) + n_states * n_features
    if model.covariance_type == "diag":
        n_params += n_states * n_features
    elif model.covariance_type == "full":
        n_params += n_states * n_features * (n_features + 1) // 2
    
    return -2.0 * log_likelihood + 2.0 * n_params


class HybridRegimeModel:
    """
    Wraps a 2-state GaussianHMM and a binary Trend indicator to expose
    a unified 4-state interface compatible with the portfolio backtester.
    """
    def __init__(self, hmm_model, scaler, trends, train_states, train_probs, transmat, startprob):
        self.hmm_model = hmm_model
        self.scaler = scaler
        self.trends = np.asarray(trends, dtype=int)
        self.train_states = np.asarray(train_states, dtype=int)
        self.train_probs = np.asarray(train_probs, dtype=float)
        self.n_components = 4
        self.transmat_ = transmat
        self.startprob_ = startprob

    def predict(self, X) -> np.ndarray:
        if len(X) == len(self.train_states):
            return self.train_states
        return self.train_states[-len(X):]

    def predict_proba(self, X) -> np.ndarray:
        if len(X) == len(self.train_probs):
            return self.train_probs
        # If length is different, calculate HMM probs and map using the corresponding trends
        hmm_probs = self.hmm_model.predict_proba(X)
        probs = np.zeros((len(X), 4), dtype=float)
        for t in range(len(X)):
            idx = -len(X) + t
            tr = self.trends[idx] if abs(idx) <= len(self.trends) else 1
            if tr == 1:
                probs[t] = [hmm_probs[t, 0], hmm_probs[t, 1], 0.0, 0.0]
            else:
                probs[t] = [0.0, 0.0, hmm_probs[t, 0], hmm_probs[t, 1]]
        return probs


def calculate_kama(series: pd.Series, er_period: int = 10, fast: int = 2, slow: int = 30) -> pd.Series:
    """Calculates Kaufman's Adaptive Moving Average (KAMA)."""
    change = series.diff(er_period).abs()
    volatility = series.diff(1).abs().rolling(window=er_period).sum()
    
    er = change / volatility.replace(0, np.nan)
    er = er.fillna(0)
    
    fast_alpha = 2.0 / (fast + 1)
    slow_alpha = 2.0 / (slow + 1)
    
    sc = (er * (fast_alpha - slow_alpha) + slow_alpha) ** 2
    
    kama = np.zeros_like(series.values, dtype=float)
    kama[:] = np.nan
    
    first_valid = sc.first_valid_index()
    if first_valid is None:
        return pd.Series(kama, index=series.index)
        
    start_idx = series.index.get_loc(first_valid)
    kama[start_idx] = series.iloc[start_idx]
    
    prices = series.values
    sc_vals = sc.values
    
    for i in range(start_idx + 1, len(series)):
        kama[i] = kama[i-1] + sc_vals[i] * (prices[i] - kama[i-1])
        
    return pd.Series(kama, index=series.index)


def prepare_vnindex_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes hybrid HMM features for VNINDEX: KAMA Trend, Log Returns, 20D Volatility, Log Volume Ratio.
    df must have 'close' and 'volume' columns.
    """
    df = df.copy().sort_index()
    if len(df) < 50:
        raise ValueError("Not enough data to calculate rolling features (need >= 50 sessions for KAMA)")
        
    df['kama'] = calculate_kama(df['close'], er_period=21, fast=5, slow=100)
    df['trend'] = (df['kama'] > df['kama'].shift(1)).astype(int)
    
    df['log_return'] = np.log(df['close'] / df['close'].shift(1))
    df['rolling_vol'] = df['log_return'].rolling(window=20).std() * np.sqrt(252)
    df['rolling_volume_ma'] = df['volume'].rolling(window=20).mean()
    df['log_volume_ratio'] = np.log(df['volume'] / df['rolling_volume_ma'].replace(0, np.nan))
    
    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    df = df.dropna().copy()
    return df


def fit_vnindex_hmm(features_df: pd.DataFrame, n_states: int = 4, random_state: int = 42) -> tuple:
    """
    Fits a 2-state HMM on standardized features, combines it with the trend filter
    to produce a 4-state Hybrid model, and returns (HybridRegimeModel, scaler).
    """
    from sklearn.preprocessing import StandardScaler
    X_raw = features_df[['log_return', 'rolling_vol', 'log_volume_ratio']].values
    
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_raw)
    
    # Train HMM Model (2 States: Low Vol vs High Vol)
    model = GaussianHMM(
        n_components=2,
        covariance_type="full",
        n_iter=500,
        tol=1e-4,
        random_state=random_state,
        init_params="mcs",
        params="mcs",
    )
    
    # Suppress output during training
    import os, sys, warnings
    devnull = open(os.devnull, "w")
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = devnull
    sys.stderr = devnull
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model.fit(X_scaled)
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        devnull.close()
        
    if is_valid_model(model):
        # State Alignment (Sort by volatility of log returns)
        states = model.predict(X_scaled)
        state_vols = []
        for k in range(2):
            mask = (states == k)
            state_vols.append(features_df.iloc[mask]['log_return'].std() if mask.any() else 999.0)
            
        idx_sort = np.argsort(state_vols)
        
        # Permute parameters
        model.startprob_ = model.startprob_[idx_sort]
        model.transmat_ = model.transmat_[np.ix_(idx_sort, idx_sort)]
        model.means_ = model.means_[idx_sort]
        model._covars_ = model._covars_[idx_sort]
        
    # Re-predict with aligned 2 HMM states (0: Low Vol, 1: High Vol)
    hmm_states = model.predict(X_scaled)
    
    # Combine HMM with trend to form 4 combined states
    trends = features_df['trend'].values.astype(int)
    combined_states = 2 * (1 - trends) + hmm_states
    
    # Generate 4-state probability matrix
    hmm_probs = model.predict_proba(X_scaled)
    T = len(X_scaled)
    combined_probs = np.zeros((T, 4), dtype=float)
    for t in range(T):
        tr = trends[t]
        p_low = hmm_probs[t, 0]
        p_high = hmm_probs[t, 1]
        if tr == 1:
            combined_probs[t] = [p_low, p_high, 0.0, 0.0]
        else:
            combined_probs[t] = [0.0, 0.0, p_low, p_high]
            
    # Calculate transition matrix and start probabilities for the 4 combined states
    # to pass validation checks
    transmat = np.zeros((4, 4), dtype=float)
    for i in range(T - 1):
        transmat[combined_states[i], combined_states[i+1]] += 1.0
    for i in range(4):
        s = transmat[i].sum()
        if s > 0:
            transmat[i] = transmat[i] / s
        else:
            transmat[i] = np.ones(4) / 4.0
            
    counts = np.bincount(combined_states, minlength=4)
    startprob = counts / float(T)
    
    hybrid_model = HybridRegimeModel(
        hmm_model=model,
        scaler=scaler,
        trends=trends,
        train_states=combined_states,
        train_probs=combined_probs,
        transmat=transmat,
        startprob=startprob
    )
    
    return hybrid_model, scaler
