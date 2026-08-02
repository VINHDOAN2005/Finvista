from __future__ import annotations
import numpy as np
import pandas as pd

def _power_iteration_top_eigval(A: np.ndarray, iters: int = 50) -> float:
    n = A.shape[0]
    v = np.ones(n) / np.sqrt(n)
    for _ in range(iters):
        Av = A @ v
        nrm = np.linalg.norm(Av)
        if nrm == 0:
            return 1.0
        v = Av / nrm
    return float(v @ (A @ v))

def project_to_simplex(v: np.ndarray) -> np.ndarray:
    if v.ndim != 1:
        v = v.ravel()
    u = np.sort(v)[::-1]
    cssv = np.cumsum(u)
    rho = np.nonzero(u * (np.arange(1, u.size + 1)) > (cssv - 1))[0][-1]
    theta = (cssv[rho] - 1.0) / (rho + 1.0)
    return np.maximum(v - theta, 0.0)

def project_to_capped_simplex(v: np.ndarray, cap: float) -> np.ndarray:
    """Projection onto {w >= 0, sum w = 1, w_i <= cap} via bisection on theta."""
    v = v.ravel()
    lo, hi = v.min() - cap, v.max()
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        s = np.clip(v - mid, 0.0, cap).sum()
        if s > 1.0:
            lo = mid
        else:
            hi = mid
    return np.clip(v - hi, 0.0, cap)

def mean_variance_long_only(
    mu, 
    cov, 
    gamma: float = 5.0, 
    max_iter: int = 500, 
    tol: float = 1e-7, 
    cap: float | None = 0.6,
    w_prev: np.ndarray | None = None,
    tcost: float = 0.0
):
    mu = np.asarray(mu, dtype=float)
    cov = np.asarray(cov, dtype=float)
    n = mu.shape[0]

    lam_max = _power_iteration_top_eigval(cov)
    step = 1.0 / (gamma * lam_max + 1e-12)

    w = np.full(n, 1.0 / n) if w_prev is None else w_prev.copy()
    for _ in range(max_iter):
        grad = -mu + gamma * (cov @ w)
        if w_prev is not None and tcost > 0.0:
            # Subgradient penalty for transaction cost
            grad += tcost * np.sign(w - w_prev)
            
        w_new = w - step * grad
        if cap is None:
            w_new = project_to_simplex(w_new)
        else:
            # ensure cap * n >= 1 to keep feasibility
            eff_cap = max(cap, 1.0 / n)
            w_new = project_to_capped_simplex(w_new, cap=eff_cap)
        if np.linalg.norm(w_new - w, 1) <= tol:
            return w_new
        w = w_new
    return w

def per_regime_weights(
    regime_stats: dict, 
    gamma: float = 5.0, 
    cap: float | None = 0.6, 
    shrink_alpha: float = 0.1,
    w_prev: np.ndarray | None = None,
    tcost: float = 0.0,
    n_assets: int | None = None
):
    """Compute long-only MV weights per regime with Ledoit-Wolf shrinkage and optional transaction cost penalty."""
    weights = {}
    for k, d in regime_stats.items():
        mu = d["mu"].values
        S = d["cov"]
        if isinstance(S, pd.DataFrame):
            S = S.values
            
        if n_assets is not None:
            mu = mu[:n_assets]
            S = S[:n_assets, :n_assets]
            
        # Try to apply Ledoit-Wolf shrinkage if returns are available
        if "returns" in d:
            try:
                from sklearn.covariance import ledoit_wolf
                r_vals = d["returns"].values
                if n_assets is not None:
                    r_vals = r_vals[:, :n_assets]
                if len(r_vals) > 5:
                    S, _ = ledoit_wolf(r_vals)
                else:
                    S = (1.0 - shrink_alpha) * S + shrink_alpha * np.diag(np.diag(S))
            except Exception:
                S = (1.0 - shrink_alpha) * S + shrink_alpha * np.diag(np.diag(S))
        else:
            S = (1.0 - shrink_alpha) * S + shrink_alpha * np.diag(np.diag(S))
            
        S = S + 1e-6 * np.eye(S.shape[0])
        weights[int(k)] = mean_variance_long_only(mu, S, gamma=gamma, cap=cap, w_prev=w_prev, tcost=tcost)
    return weights