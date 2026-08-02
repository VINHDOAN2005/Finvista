# -*- coding: utf-8 -*-
"""
🤖 FINVISTA: DEEP REINFORCEMENT LEARNING PORTFOLIO AGENT
======================================================
PyTorch-based Deep Reinforcement Learning for adaptive asset allocation.
Implements:
  1. VNWarrantEnv: Custom simulation environment for Vietnamese assets.
  2. Policy Network: Neural network policy mapping states to portfolio weights.
  3. REINFORCE Algorithm: Policy Gradient reinforcement learning solver.
  4. Benchmark Evaluator: DRL-Break vs DRL-Plain vs Markowitz vs Buy & Hold.

Author: samvo
"""

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from torch.distributions import Categorical
import os
from src.modules.regime_analysis.indicators.kalman_filter import KalmanFilterPrice

# ══════════════════════════════════════════════════════════════════════
# 1. CUSTOM TRADING ENVIRONMENT
# ══════════════════════════════════════════════════════════════════════

class VNWarrantEnv:
    """
    Simulation environment for portfolio optimization of Vietnamese assets.
    Incorporates transaction fees, slippage, and regime states.
    Now includes Kalman Filtered features, a 'CASH' asset for risk control,
    and EWMA volatility targeting.
    """
    def __init__(self, asset_returns: pd.DataFrame, regime_probs: pd.Series, transaction_fee: float = 0.002,
                 target_vol: float = None, ewma_lambda: float = 0.94):
        self.returns = asset_returns.values
        self.regime_probs = regime_probs.values
        self.asset_names = list(asset_returns.columns) + ["CASH"]
        self.num_assets = len(self.asset_names) # Now n_stocks + 1
        self.num_stocks = len(asset_returns.columns)
        self.fee = transaction_fee
        self.T = len(asset_returns)
        self.target_vol = target_vol  # Annualized volatility target
        self.ewma_lambda = ewma_lambda  # EWMA decay factor
        
        # Initialize Kalman Filters for each STOCK to denoise returns
        self.kalman_filters = [KalmanFilterPrice(process_variance=1e-6, measurement_variance=1e-4) for _ in range(self.num_stocks)]
        self.kalman_values = np.zeros(self.num_stocks)
        
        # EWMA covariance matrix for volatility targeting
        self.ewma_cov = np.cov(self.returns.T) if self.returns.shape[0] > 1 else np.eye(self.num_stocks)
        
        self.current_step = 0
        self.portfolio_weights = np.ones(self.num_assets) / self.num_assets
        self.nav = 100_000_000.0  # Start with 100M VND
        self.initial_nav = 100_000_000.0
        self.nav_history = []
        self.peak_nav = self.nav

    def reset(self) -> np.ndarray:
        self.current_step = 0
        self.portfolio_weights = np.ones(self.num_assets) / self.num_assets
        self.nav = self.initial_nav
        self.nav_history = [self.nav]
        self.peak_nav = self.nav
        
        # Reset Kalman Filters
        for kf in self.kalman_filters:
            kf.reset()
        self.kalman_values = np.zeros(self.num_stocks)
        
        return self._get_observation()

    def _get_observation(self) -> np.ndarray:
        # State consists of:
        # - Regime probability at step t (1 element)
        # - Past 5-day historical returns for all stocks (5 * num_stocks elements)
        # - Kalman-smoothed returns for stocks (num_stocks elements)
        # - Current portfolio weights (num_assets elements)
        t = self.current_step
        regime_val = self.regime_probs[t] if t < len(self.regime_probs) else 0.5
        
        # Gather historical returns (pad with zeros if t < 5)
        hist_returns = np.zeros((5, self.num_stocks))
        start_idx = max(0, t - 5)
        end_idx = t
        if end_idx > 0:
            slice_rets = self.returns[start_idx:end_idx]
            hist_returns[-len(slice_rets):] = slice_rets
            
        obs = np.concatenate([
            [regime_val],
            hist_returns.flatten(),
            self.kalman_values,
            self.portfolio_weights
        ])
        return obs

    def step(self, action_weights: np.ndarray) -> tuple:
        """
        Executes one step in the environment.
        action_weights: new portfolio weights (sums to 1, including CASH)
        """
        t = self.current_step
        
        # Update Kalman filters with current returns for the NEXT observation
        for i in range(self.num_stocks):
            self.kalman_values[i] = self.kalman_filters[i].update(self.returns[t, i])
        
        # Update EWMA covariance matrix for volatility targeting
        if t > 0:
            ret_t = self.returns[t:t+1, :self.num_stocks]  # Current returns
            # EWMA update: Sigma_t = lambda * Sigma_{t-1} + (1-lambda) * r_t * r_t'
            self.ewma_cov = self.ewma_lambda * self.ewma_cov + (1 - self.ewma_lambda) * (ret_t.T @ ret_t)
            
        # Apply volatility targeting if enabled
        if self.target_vol is not None and self.target_vol > 0:
            # Extract stock weights only (exclude CASH)
            stock_weights = action_weights[:self.num_stocks]
            cash_weight = action_weights[self.num_stocks]
            
            # Calculate current portfolio volatility
            if np.sum(stock_weights) > 1e-8:
                port_var = stock_weights @ self.ewma_cov @ stock_weights
                cur_vol = np.sqrt(port_var) * np.sqrt(252)  # Annualized
                
                # Scale weights to target volatility
                if cur_vol > 1e-8:
                    scale_factor = self.target_vol / cur_vol
                    # Cap scaling to avoid extreme positions
                    scale_factor = np.clip(scale_factor, 0.5, 2.0)
                    stock_weights = stock_weights * scale_factor
                    
                    # Re-normalize: if scaled weights exceed 1, shift excess to cash
                    total_stock_weight = np.sum(stock_weights)
                    if total_stock_weight > 1.0:
                        stock_weights = stock_weights / total_stock_weight
                        cash_weight = 0.0
                    else:
                        cash_weight = 1.0 - total_stock_weight
                
                # Reconstruct action weights
                action_weights = np.concatenate([stock_weights, [cash_weight]])
            
        # 1. Calculate transaction fee due to rebalancing (only stocks have fees, cash is 'free' or lower)
        # For simplicity, we apply fee to any weight change
        weight_change = np.sum(np.abs(action_weights - self.portfolio_weights))
        fee_cost = self.nav * weight_change * self.fee
        
        # Update weights
        self.portfolio_weights = action_weights
        
        # 2. Calculate asset return at step t
        # Stock returns are from self.returns, Cash return is 0
        full_returns = np.zeros(self.num_assets)
        full_returns[:self.num_stocks] = self.returns[t]
        full_returns[self.num_stocks] = 0.0001 # Small daily return for cash (~3.6% annual)
        
        # Portfolio return
        port_ret = np.dot(self.portfolio_weights, full_returns)
        
        # 3. Calculate new NAV
        new_nav = (self.nav - fee_cost) * (1.0 + port_ret)
        
        # Reward is log returns minus drawdown penalty
        reward = np.log(max(new_nav / self.nav, 1e-5))
        
        # Drawdown calculation
        self.nav = new_nav
        self.nav_history.append(self.nav)
        self.peak_nav = max(self.peak_nav, self.nav)
        drawdown = (self.peak_nav - self.nav) / self.peak_nav
        
        # Penalize large drawdowns (risk control)
        if drawdown > 0.15:
            reward -= 0.02 * (drawdown - 0.15)
            
        self.current_step += 1
        done = (self.current_step >= self.T - 1)
        
        return self._get_observation(), reward, done, {"nav": self.nav, "drawdown": drawdown}

# ══════════════════════════════════════════════════════════════════════
# 2. DEEP NEURAL NETWORK POLICY
# ══════════════════════════════════════════════════════════════════════

class PolicyNetwork(nn.Module):
    """
    Parametrized policy mapping state observations to a softmax allocation vector.
    """
    def __init__(self, state_dim: int, action_dim: int):
        super(PolicyNetwork, self).__init__()
        self.net = nn.Sequential(
            nn.Linear(state_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, action_dim)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        logits = self.net(x)
        # Apply softmax to output valid portfolio weights (0 to 1, summing to 1)
        return torch.softmax(logits, dim=-1)

# ══════════════════════════════════════════════════════════════════════
# 3. REINFORCE AGENT CLASS
# ══════════════════════════════════════════════════════════════════════

class DRLPortfolioAgent:
    """
    Policy Gradient reinforcement learning agent with per-regime MV initialization.
    """
    def __init__(self, state_dim: int, action_dim: int, lr: float = 0.002, gamma: float = 0.99,
                 regime_stats: dict = None, shrink_alpha: float = 0.1):
        self.policy = PolicyNetwork(state_dim, action_dim)
        self.optimizer = optim.Adam(self.policy.parameters(), lr=lr)
        self.gamma = gamma
        self.action_dim = action_dim
        self.regime_stats = regime_stats
        
        # Initialize policy with per-regime MV weights if provided
        if regime_stats is not None:
            self.initialize_with_regime_mv(regime_stats, shrink_alpha)
    
    def initialize_with_regime_mv(self, regime_stats: dict, shrink_alpha: float = 0.1):
        """
        Initialize policy network weights based on per-regime mean-variance optimal weights.
        This provides a strong prior for the DRL agent to learn from.
        """
        import torch.nn.init as init
        
        # Compute average MV weights across all regimes
        avg_weights = []
        for k, stats in regime_stats.items():
            mu = stats["mu"].values
            cov = stats["cov"].values
            
            # Apply diagonal shrinkage for stability
            cov_shrunk = (1 - shrink_alpha) * cov + shrink_alpha * np.diag(np.diag(cov))
            cov_shrunk = cov_shrunk + 1e-6 * np.eye(cov_shrunk.shape[0])
            
            # Simple MV optimization (equal risk contribution approximation)
            n = len(mu)
            inv_cov = np.linalg.inv(cov_shrunk)
            w = inv_cov @ mu
            
            # Long-only constraint
            w = np.maximum(w, 0)
            if w.sum() > 0:
                w = w / w.sum()
            else:
                w = np.ones(n) / n
            
            avg_weights.append(w)
        
        # Average across regimes
        init_weights = np.mean(avg_weights, axis=0)
        
        # Add cash allocation (last asset)
        init_weights = np.concatenate([init_weights * 0.9, [0.1]])
        
        # Initialize the final layer to output these weights
        # We set the bias to produce the desired weights when input is zero
        with torch.no_grad():
            # Get the final layer weights
            final_layer = self.policy.net[-1]
            
            # Set bias to log(init_weights) to produce desired softmax output
            # softmax(x) = w => x = log(w) + constant
            log_weights = np.log(init_weights + 1e-8)
            final_layer.bias.data = torch.FloatTensor(log_weights)
            
            # Initialize weights to small values to preserve bias influence
            init.normal_(final_layer.weight.data, mean=0.0, std=0.01)
        
        print(f"✅ Policy initialized with per-regime MV weights: {init_weights.round(4)}")

    def select_action(self, state: np.ndarray, evaluate: bool = False) -> tuple:
        state_t = torch.FloatTensor(state)
        weights = self.policy(state_t)
        
        if evaluate:
            # During evaluation, return the deterministic weights directly
            return weights.detach().numpy(), torch.tensor(0.0)
            
        # During training, sample weights around the predicted policy using a Dirichlet-like log-prob
        # or use simple Gaussian noise. For policy gradients, we can treat the weights as a distribution.
        # Alternatively, map action outputs to discrete portfolio adjustments or use continuous policy gradient.
        # Simplification: treat actions as logits, sample from a categorical distribution over assets to overweight,
        # then blend with equal-weight baseline.
        dist = Categorical(weights)
        action = dist.sample()
        
        # Build stochastic action weights
        stochastic_weights = np.zeros(self.action_dim)
        stochastic_weights[action.item()] = 0.60
        remaining_weight = 0.40 / (self.action_dim - 1) if self.action_dim > 1 else 0.40
        for i in range(self.action_dim):
            if i != action.item():
                stochastic_weights[i] = remaining_weight
                
        return stochastic_weights, dist.log_prob(action)

    def train_agent(self, env: VNWarrantEnv, episodes: int = 150) -> list:
        episode_rewards = []
        
        for ep in range(episodes):
            state = env.reset()
            log_probs = []
            rewards = []
            done = False
            
            while not done:
                action, log_prob = self.select_action(state, evaluate=False)
                state, reward, done, _ = env.step(action)
                log_probs.append(log_prob)
                rewards.append(reward)
                
            # Compute policy gradient update
            discounted_rewards = []
            R = 0
            for r in reversed(rewards):
                R = r + self.gamma * R
                discounted_rewards.insert(0, R)
                
            discounted_rewards = torch.FloatTensor(discounted_rewards)
            # Normalize rewards for gradient stability
            if len(discounted_rewards) > 1:
                discounted_rewards = (discounted_rewards - discounted_rewards.mean()) / (discounted_rewards.std() + 1e-8)
                
            policy_loss = []
            for lp, r_t in zip(log_probs, discounted_rewards):
                policy_loss.append(-lp * r_t)
                
            if policy_loss:
                self.optimizer.zero_grad()
                loss = torch.stack(policy_loss).sum()
                loss.backward()
                self.optimizer.step()
                
            ep_reward = sum(rewards)
            episode_rewards.append(ep_reward)
            
        return episode_rewards

    def save(self, filepath: str):
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        torch.save(self.policy.state_dict(), filepath)

    def load(self, filepath: str):
        if os.path.exists(filepath):
            self.policy.load_state_dict(torch.load(filepath))
            self.policy.eval()

# ══════════════════════════════════════════════════════════════════════
# 4. BENCHMARK COMPARATOR
# ══════════════════════════════════════════════════════════════════════

def generate_mock_data(periods: int = 500) -> tuple:
    """Generates realistic mock data containing structural breaks for testing."""
    np.random.seed(42)
    # 5 underlyings
    assets = ['ACB', 'HPG', 'VCB', 'VIC', 'FPT']
    
    # 2 regimes: 0 (Normal: Bullish, low vol), 1 (Crisis: Bearish, high vol)
    regime = 0
    regime_probs = []
    returns_list = []
    
    current_prices = np.array([100.0, 50.0, 80.0, 60.0, 120.0])
    
    for t in range(periods):
        # Markov regime transitions
        if regime == 0:
            if np.random.rand() < 0.04:  # 4% chance to enter crisis
                regime = 1
        else:
            if np.random.rand() < 0.10:  # 10% chance to recover
                regime = 0
                
        # Generate returns based on regime
        if regime == 0:
            # Low vol, positive mean
            rets = np.random.normal(0.0008, 0.010, len(assets))
            prob = 0.10 + np.random.rand() * 0.15
        else:
            # High vol, negative mean
            rets = np.random.normal(-0.002, 0.035, len(assets))
            prob = 0.75 + np.random.rand() * 0.20
            
        regime_probs.append(prob)
        returns_list.append(rets)
        
    df_returns = pd.DataFrame(returns_list, columns=assets)
    s_regime_probs = pd.Series(regime_probs)
    return df_returns, s_regime_probs

def run_markowitz_allocation(returns: pd.DataFrame) -> np.ndarray:
    """Mean-Variance Optimization weights (max Sharpe)."""
    mean_rets = returns.mean()
    cov_matrix = returns.cov()
    n = len(returns.columns)
    
    # Monte Carlo Sharpe optimization
    best_sharpe = -np.inf
    best_weights = np.ones(n) / n
    for _ in range(2000):
        w = np.random.dirichlet(np.ones(n))
        port_ret = np.dot(w, mean_rets)
        port_vol = np.sqrt(np.dot(w.T, np.dot(cov_matrix, w)))
        if port_vol > 0:
            sharpe = port_ret / port_vol
            if sharpe > best_sharpe:
                best_sharpe = sharpe
                best_weights = w
    return best_weights

def calculate_performance_metrics(nav_history: list) -> dict:
    """Calculates CAGR, Sharpe Ratio, and Max Drawdown."""
    navs = np.array(nav_history)
    returns = np.diff(navs) / navs[:-1]
    
    # CAGR (assuming daily data, 252 trading days per year)
    total_days = len(nav_history)
    cagr = (navs[-1] / navs[0]) ** (252.0 / total_days) - 1.0
    
    # Sharpe Ratio
    std = returns.std()
    sharpe = (returns.mean() / std) * np.sqrt(252) if std > 0 else 0.0
    
    # Max Drawdown
    peaks = np.maximum.accumulate(navs)
    drawdowns = (peaks - navs) / peaks
    max_dd = -np.max(drawdowns)
    
    return {
        "cagr": cagr * 100.0,
        "sharpe": sharpe,
        "max_dd": max_dd * 100.0
    }

def evaluate_drl_vs_benchmarks(returns: pd.DataFrame, regime_probs: pd.Series, model_path: str = None) -> dict:
    """
    Evaluates 4 strategies: DRL-Break, DRL-Plain, Markowitz (MVO), and Buy & Hold.
    """
    assets = list(returns.columns)
    n_assets = len(assets)
    
    # 1. Initialize environments
    env_break = VNWarrantEnv(returns, regime_probs)
    # Plain environment has a constant regime observation of 0.5 (unaware of structural breaks)
    env_plain = VNWarrantEnv(returns, pd.Series(np.ones(len(regime_probs)) * 0.5))
    env_mvo = VNWarrantEnv(returns, regime_probs)
    env_bah = VNWarrantEnv(returns, regime_probs)
    
    # 2. DRL-Break Agent
    n_stocks = n_assets
    n_total_assets = n_stocks + 1 # Stocks + Cash
    agent_break = DRLPortfolioAgent(state_dim=1 + 6*n_stocks + n_total_assets, action_dim=n_total_assets)
    if model_path and os.path.exists(model_path):
        agent_break.load(model_path)
    else:
        # Quick train for testing
        agent_break.train_agent(env_break, episodes=40)
        
    # Evaluate DRL-Break
    state = env_break.reset()
    done = False
    while not done:
        weights, _ = agent_break.select_action(state, evaluate=True)
        state, _, done, _ = env_break.step(weights)
        
    # 3. DRL-Plain Agent (trained without regime inputs)
    agent_plain = DRLPortfolioAgent(state_dim=1 + 6*n_stocks + n_total_assets, action_dim=n_total_assets)
    agent_plain.train_agent(env_plain, episodes=40)
    
    state = env_plain.reset()
    done = False
    while not done:
        weights, _ = agent_plain.select_action(state, evaluate=True)
        state, _, done, _ = env_plain.step(weights)
        
    # 4. Markowitz (MVO) rebalanced periodically (every 20 days)
    env_mvo.reset()
    mvo_weights = run_markowitz_allocation(returns)
    for t in range(len(returns) - 1):
        if t % 20 == 0:
            # Re-evaluate covariance using sliding window
            window = returns.iloc[max(0, t-60):t+1] if t > 10 else returns
            mvo_weights = run_markowitz_allocation(window)
        env_mvo.step(mvo_weights)
        
    # 5. Buy & Hold (Equal weights, no rebalancing)
    env_bah.reset()
    bah_weights = np.ones(n_assets) / n_assets
    for t in range(len(returns) - 1):
        env_bah.step(bah_weights)
        
    # Compile results
    results = {
        "DRL-Break": calculate_performance_metrics(env_break.nav_history),
        "DRL-Plain": calculate_performance_metrics(env_plain.nav_history),
        "Markowitz": calculate_performance_metrics(env_mvo.nav_history),
        "Buy & Hold": calculate_performance_metrics(env_bah.nav_history)
    }
    
    # Print comparison table
    print("\n" + "=" * 80)
    print(" 🏆 CHIẾN LƯỢC TỐI ƯU HÓA DANH MỤC: DRL VS BENCHMARKS")
    print("=" * 80)
    print(f" {'Chiến lược':<20} | {'CAGR (%)':>12} | {'Sharpe Ratio':>15} | {'Max Drawdown (%)':>20}")
    print("-" * 80)
    for name, metrics in results.items():
        print(f" {name:<20} | {metrics['cagr']:>+11.2f}% | {metrics['sharpe']:>15.4f} | {metrics['max_dd']:>19.2f}%")
    print("=" * 80 + "\n")
    
    return results

if __name__ == "__main__":
    # Test generation and evaluation
    returns, regimes = generate_mock_data()
    evaluate_drl_vs_benchmarks(returns, regimes)
