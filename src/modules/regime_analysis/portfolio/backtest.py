from __future__ import annotations
import numpy as np
import pandas as pd
from .utils import ewma_cov, project_weights_to_simplex, project_to_subsimplex

def _period_end_flags(index: pd.DatetimeIndex, freq: str = 'M') -> np.ndarray:
    # True on the last date present in each period of 'freq' (e.g., 'M', 'Q')
    p = index.to_period(freq).to_numpy()
    return np.r_[p[1:] != p[:-1], True]

# In-sample backtest (soft regime mixture)
def run_backtest(
    prices: pd.DataFrame,
    returns: pd.DataFrame,
    regime_probs: pd.DataFrame,
    regime_weights: dict,
    tcost: float = 0.0005,
    prob_threshold: float = 0.0,
    rebalance_freq: str = 'M',
    state_exposures: dict | None = None,
    exposure_mode: str = 'soft'
):
    idx = returns.index
    tickers = list(returns.columns)
    T, N = returns.shape

    is_reb = _period_end_flags(idx, rebalance_freq)
    W = np.zeros((T, N), dtype=float)
    w = np.full(N, 1.0 / N)
    W[0] = w
    cost_factor = np.ones(T, dtype=float)
    P = regime_probs.values  # (T, K)

    for t in range(1, T):
        if is_reb[t]:
            pk = P[t]
            if prob_threshold > 0.0 and pk.max() < prob_threshold:
                W[t] = w
                continue
            w_mix = np.zeros(N)
            for k, wk in regime_weights.items():
                w_mix += pk[int(k)] * wk
            
            # Apply top-down exposure scale based on HMM states
            if state_exposures is None:
                state_exposures = {0: 1.0, 1: 0.6, 2: 0.3, 3: 0.0}
            elif isinstance(state_exposures, list):
                state_exposures = {i: v for i, v in enumerate(state_exposures)}
            if exposure_mode == 'hard':
                max_state = int(np.argmax(pk))
                exposure = state_exposures.get(max_state, 0.5)
            else:
                exposure = sum(pk[i] * state_exposures.get(i, 0.5) for i in range(len(pk)))
            w_mix = w_mix * exposure
            
            w_mix = project_to_subsimplex(w_mix)
            turnover = np.abs(w_mix - w).sum()
            if turnover > 0:
                cost_factor[t] = 1.0 - tcost * turnover
            w = w_mix
        W[t] = w

    R = returns.values
    port_ret = np.einsum('tn,tn->t', R, W)
    equity = np.cumprod((1.0 + port_ret) * cost_factor, dtype=float)
    return pd.Series(equity, index=idx, name='equity'), pd.DataFrame(W, index=idx, columns=tickers)

# Rolling OOS backtest (re-fit model each period) with vol targeting
def run_backtest_rolling(
    returns: pd.DataFrame,
    fit_fn,
    weight_fn,
    window: int = 252*3,
    rebalance_freq: str = 'M',
    tcost: float = 0.0005,
    target_vol: float | None = 0.12,
    prob_threshold: float = 0.0,
    exog_features: pd.DataFrame | None = None,
    vnindex_data: pd.DataFrame | None = None,
    n_states: int = 4,
    state_exposures: dict | None = None,
    exposure_mode: str = 'soft'
):
    idx = returns.index
    tickers = list(returns.columns)
    T, N = returns.shape
    is_reb = _period_end_flags(idx, rebalance_freq)
    W = np.zeros((T, N), dtype=float)
    w = np.full(N, 1.0 / N)
    W[0] = w
    cost_factor = np.ones(T, dtype=float)

    from .regime_model import posterior_probs, viterbi_path, regime_stats_by_label, is_valid_model

    for t in range(1, T):
        if is_reb[t]:
            start = max(0, t - window)
            r_win = returns.iloc[start:t]
            if len(r_win) < max(126, N * 20):
                W[t] = w
                continue

            used_vnindex = False
            if vnindex_data is not None:
                from .regime_model import prepare_vnindex_features, fit_vnindex_hmm
                try:
                    # Align VNINDEX window up to the last index of r_win
                    vn_win = vnindex_data.loc[vnindex_data.index <= r_win.index[-1]].iloc[-window:]
                    if len(vn_win) >= 126:
                        feat_win = prepare_vnindex_features(vn_win)
                        model_vn, scaler_vn = fit_vnindex_hmm(feat_win, n_states=n_states)
                        
                        if is_valid_model(model_vn):
                            # Predict state probability for the last session
                            X_last = feat_win[['log_return', 'rolling_vol', 'log_volume_ratio']].values[-1:]
                            X_last_scaled = scaler_vn.transform(X_last)
                            pk = model_vn.predict_proba(X_last_scaled)[0]
                            
                            # Generate labels and calculate stats for assets based on VNINDEX states
                            X_all_scaled = scaler_vn.transform(feat_win[['log_return', 'rolling_vol', 'log_volume_ratio']].values)
                            vn_states = model_vn.predict(X_all_scaled)
                            
                            # Align asset returns in r_win with the dates of feat_win
                            r_win_aligned = r_win.reindex(feat_win.index).dropna()
                            labels_series = pd.Series(vn_states, index=feat_win.index)
                            labels_series = labels_series.reindex(r_win_aligned.index).dropna().astype(int)
                            
                            # Stats of assets grouped by VNINDEX states
                            stats = regime_stats_by_label(r_win_aligned, labels_series)
                            
                            try:
                                reg_w = weight_fn(stats, w_prev=w, tcost=tcost, n_assets=N)
                            except TypeError:
                                try:
                                    reg_w = weight_fn(stats, w_prev=w, tcost=tcost)
                                except TypeError:
                                    reg_w = weight_fn(stats)
                            
                            used_vnindex = True
                except Exception as e:
                    print(f"⚠️ Rolling VN-Index HMM fit failed at index {t}: {e}. Falling back to asset-level fit.")

            if not used_vnindex:
                if exog_features is not None:
                    feat_win = pd.concat([r_win, exog_features.iloc[start:t]], axis=1).dropna()
                else:
                    feat_win = r_win

                model = fit_fn(feat_win)

                if not is_valid_model(model):
                    W[t] = w
                    continue
                probs = posterior_probs(model, feat_win)
                labels = viterbi_path(model, feat_win)
                stats = regime_stats_by_label(feat_win, labels)
                try:
                    reg_w = weight_fn(stats, w_prev=w, tcost=tcost, n_assets=N)
                except TypeError:
                    try:
                        reg_w = weight_fn(stats, w_prev=w, tcost=tcost)
                    except TypeError:
                        reg_w = weight_fn(stats)

                pk = probs.iloc[-1].to_numpy()

            if prob_threshold > 0.0 and pk.max() < prob_threshold:
                W[t] = w
                continue

            w_mix = np.zeros(N)
            for k, wk in reg_w.items():
                w_mix += pk[int(k)] * wk

            if not np.isfinite(w_mix).all() or w_mix.sum() <= 0:
                W[t] = w
                continue

            # Apply top-down exposure scale based on HMM states
            if state_exposures is None:
                state_exposures = {0: 1.0, 1: 0.6, 2: 0.3, 3: 0.0}
            elif isinstance(state_exposures, list):
                state_exposures = {i: v for i, v in enumerate(state_exposures)}
            if exposure_mode == 'hard':
                max_state = int(np.argmax(pk))
                exposure = state_exposures.get(max_state, 0.5)
            else:
                exposure = sum(pk[i] * state_exposures.get(i, 0.5) for i in range(len(pk)))
            w_mix = w_mix * exposure

            # Volatility targeting
            if target_vol is not None and target_vol > 0:
                cov_fore = ewma_cov(r_win, lam=0.94)
                cur_vol = np.sqrt(w_mix @ cov_fore @ w_mix) * np.sqrt(252.0)
                if cur_vol > 1e-12:
                    scale = target_vol / cur_vol
                    w_mix *= scale

            w_new = project_to_subsimplex(w_mix)
            turnover = np.abs(w_new - w).sum()
            if turnover > 0:
                cost_factor[t] = 1.0 - tcost * turnover
            w = w_new
        W[t] = w

    R = returns.values
    port_ret = np.einsum('tn,tn->t', R, W)
    equity = np.cumprod((1.0 + port_ret) * cost_factor, dtype=float)
    return pd.Series(equity, index=idx, name='equity'), pd.DataFrame(W, index=idx, columns=tickers)

# Static baseline (no regime switching)
def static_backtest(returns: pd.DataFrame, static_w: np.ndarray):
    R = returns.values
    port_ret = R @ static_w
    equity = np.cumprod(1.0 + port_ret)
    return pd.Series(equity, index=returns.index, name='equity')