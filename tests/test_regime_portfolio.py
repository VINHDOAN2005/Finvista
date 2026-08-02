import numpy as np
import pandas as pd
import pytest
from src.modules.regime_analysis.portfolio.optimiser import mean_variance_long_only
from src.modules.regime_analysis.portfolio.utils import sharpe_ratio, max_drawdown, annualise_return, annualise_vol, project_weights_to_simplex, project_to_subsimplex


def test_mean_variance_weights_valid():
    mu = np.array([0.10, 0.05, 0.02])
    cov = np.diag([0.02, 0.01, 0.03]).astype(float)
    w = mean_variance_long_only(mu, cov, gamma=5.0, cap=1.0)
    assert w.shape == (3,)
    assert (w >= -1e-12).all()
    assert abs(w.sum() - 1.0) < 1e-6


def test_mean_variance_cap_respected():
    mu = np.array([0.10, 0.05, 0.02, 0.08])
    cov = np.diag([0.02, 0.01, 0.03, 0.015]).astype(float)
    cap = 0.5
    w = mean_variance_long_only(mu, cov, gamma=3.0, cap=cap)
    assert (w <= cap + 1e-6).all()
    assert abs(w.sum() - 1.0) < 1e-6


def test_simplex_projection_valid():
    v = np.array([0.5, 0.3, 0.2])
    w = project_weights_to_simplex(v)
    assert abs(w.sum() - 1.0) < 1e-6
    assert (w >= 0).all()


def test_subsimplex_projection_valid():
    # Case 1: elements sum <= 1.0 and >= 0, should keep them as is
    v = np.array([0.2, 0.3, 0.1])
    w = project_to_subsimplex(v)
    assert np.allclose(w, np.array([0.2, 0.3, 0.1]))
    
    # Case 2: elements sum > 1.0, should project onto standard simplex
    v = np.array([0.8, 0.4, 0.2])
    w = project_to_subsimplex(v)
    assert abs(w.sum() - 1.0) < 1e-6
    assert (w >= 0).all()
    
    # Case 3: elements contain negative, but sum of positive is <= 1.0
    v = np.array([0.5, -0.2, 0.3])
    w = project_to_subsimplex(v)
    assert np.allclose(w, np.array([0.5, 0.0, 0.3]))


def test_simplex_projection_nan_fallback():
    v = np.array([np.nan, np.nan, np.nan])
    w = project_weights_to_simplex(v)
    assert np.isfinite(w).all()
    assert abs(w.sum() - 1.0) < 1e-6


def test_simplex_projection_zeros_fallback():
    v = np.array([0.0, 0.0, 0.0])
    w = project_weights_to_simplex(v)
    assert np.isfinite(w).all()
    assert abs(w.sum() - 1.0) < 1e-6


def test_sharpe_ratio():
    rng = np.random.default_rng(0)
    r = rng.normal(0.001, 0.01, 500)
    s = sharpe_ratio(r)
    assert np.isfinite(s)
    assert s > 0


def test_max_drawdown_negative():
    equity = np.array([1.0, 1.1, 0.9, 1.05, 0.95])
    dd = max_drawdown(equity)
    assert dd < 0


def test_annualise_return():
    assert annualise_return(0.001) > 0


def test_annualise_vol():
    assert annualise_vol(0.01) == pytest.approx(0.01 * np.sqrt(252), rel=1e-5)


def test_sortino_ratio():
    from src.modules.regime_analysis.portfolio.utils import sortino_ratio
    r = np.array([0.01, -0.02, 0.015, -0.01, 0.005])
    s = sortino_ratio(r)
    assert np.isfinite(s)


def test_calmar_ratio():
    from src.modules.regime_analysis.portfolio.utils import calmar_ratio
    c = calmar_ratio(0.12, -0.20)
    assert c == 0.60
    assert np.isnan(calmar_ratio(0.12, 0.0))


def test_align_states():
    from src.modules.regime_analysis.portfolio.regime_model import align_states
    from hmmlearn.hmm import GaussianHMM
    model = GaussianHMM(n_components=3, covariance_type="diag")
    model.n_features = 1
    model.covars_ = np.array([[0.09], [0.01], [0.04]])
    model.means_ = np.array([[0.1], [0.2], [0.3]])
    model.startprob_ = np.array([0.2, 0.5, 0.3])
    model.transmat_ = np.array([[0.5, 0.3, 0.2], [0.1, 0.8, 0.1], [0.2, 0.2, 0.6]])
    
    aligned = align_states(model)
    assert aligned.covars_[0, 0] == 0.01
    assert aligned.covars_[1, 0] == 0.04
    assert aligned.covars_[2, 0] == 0.09
    assert aligned.startprob_[0] == 0.5
    assert aligned.startprob_[1] == 0.3
    assert aligned.startprob_[2] == 0.2


def test_backtest_exposure_modes():
    from src.modules.regime_analysis.portfolio.backtest import run_backtest
    
    # Create mock data
    idx = pd.date_range(start="2026-06-01", periods=5, freq="D")
    prices = pd.DataFrame({
        "A": [10.0, 10.1, 10.2, 10.3, 10.4],
        "B": [20.0, 20.2, 20.4, 20.6, 20.8]
    }, index=idx)
    returns = prices.pct_change().dropna()
    
    # 4 rows of returns
    regime_probs = pd.DataFrame([
        [0.8, 0.2, 0.0],  # mostly state 0 (Bullish)
        [0.1, 0.8, 0.1],  # mostly state 1 (Sideways)
        [0.0, 0.1, 0.9],  # mostly state 2 (Bearish)
        [0.4, 0.4, 0.2]   # blended state
    ], index=returns.index, columns=["state_0", "state_1", "state_2"])
    
    regime_weights = {
        0: np.array([0.6, 0.4]),
        1: np.array([0.5, 0.5]),
        2: np.array([0.3, 0.7])
    }
    
    custom_exposures = {0: 1.0, 1: 0.7, 2: 0.1}
    
    # Test soft exposure mode
    eq_soft, w_soft = run_backtest(
        prices, returns, regime_probs, regime_weights,
        tcost=0.0, rebalance_freq='D',
        state_exposures=custom_exposures, exposure_mode='soft'
    )
    
    # For day 2: pk = [0.1, 0.8, 0.1]
    # base w_mix = 0.1 * [0.6, 0.4] + 0.8 * [0.5, 0.5] + 0.1 * [0.3, 0.7] = [0.49, 0.51]
    # exposure = 0.1 * 1.0 + 0.8 * 0.7 + 0.1 * 0.1 = 0.67
    # w_final = [0.49, 0.51] * 0.67 = [0.3283, 0.3417]
    assert np.allclose(w_soft.iloc[1].values, np.array([0.3283, 0.3417]))
    
    # Test hard exposure mode
    eq_hard, w_hard = run_backtest(
        prices, returns, regime_probs, regime_weights,
        tcost=0.0, rebalance_freq='D',
        state_exposures=custom_exposures, exposure_mode='hard'
    )
    # For day 2: max prob state is 1 (prob 0.8). exposure = 0.7
    # w_final = [0.49, 0.51] * 0.7 = [0.343, 0.357]
    assert np.allclose(w_hard.iloc[1].values, np.array([0.343, 0.357]))
    
    # For day 3 (index 2): pk = [0.0, 0.1, 0.9] -> max state is 2. exposure = 0.1
    # base w_mix = 0.0 * [0.6, 0.4] + 0.1 * [0.5, 0.5] + 0.9 * [0.3, 0.7] = [0.32, 0.68]
    # w_final = [0.32, 0.68] * 0.1 = [0.032, 0.068]
    assert np.allclose(w_hard.iloc[2].values, np.array([0.032, 0.068]))

