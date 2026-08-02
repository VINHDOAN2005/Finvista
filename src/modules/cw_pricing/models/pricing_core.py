# -*- coding: utf-8 -*-
"""
🏆 VN-QUANT: QUANTITATIVE COVERED WARRANT PRICING ENGINE
======================================================
Consolidated Core Mathematical calculations for Covered Warrants (CW).
European Option Black-Scholes formula, Greeks, Newton-Raphson Implied Volatility.
Scoring strategies: Safe, Balanced, Aggressive.

Author: samvo
Version: 2.0 (Super Minimalist)
"""

import numpy as np
import pandas as pd
from scipy.stats import norm
from typing import Dict, Tuple, Any
import math
try:
    from numba import njit
except ImportError:
    # Fallback to a dummy decorator if numba is not installed
    def njit(f): return f

try:
    from src.core.utils import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

# ==========================================================
# 0. NUMBA-COMPATIBLE FAST MATH
# ==========================================

@njit
def n_pdf(x: float) -> float:
    """Fast Normal PDF."""
    return math.exp(-0.5 * x**2) / math.sqrt(2.0 * math.pi)

@njit
def n_cdf(x: float) -> float:
    """Fast Normal CDF using math.erf."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

# Default Volatility for Fair Value comparison (SSC Benchmark approximation)
DEFAULT_VOLATILITY = 0.45

def fetch_dynamic_risk_free_rate() -> float:
    """
    Fetch the live Vietnam 1-Year Government Bond Yield from WorldGovernmentBonds.
    Returns the yield as a float (e.g. 0.0352 for 3.52%).
    Falls back to 0.045 if the request fails or is blocked.
    """
    url = "https://www.worldgovernmentbonds.com/wp-json/country/v1/main"
    body = {
        "GLOBALVAR": {
            "JS_VARIABLE": "jsGlobalVars",
            "FUNCTION": "Country",
            "DOMESTIC": True,
            "ENDPOINT": "http://www.worldgovernmentbonds.com/wp-json/country/v1/historical",
            "DATE_RIF": "2099-12-31",
            "OBJ": None,
            "COUNTRY1": {
                "SYMBOL": "58",
                "PAESE": "Vietnam",
                "PAESE_UPPERCASE": "VIETNAM",
                "BANDIERA": "vn",
                "URL_PAGE": "vietnam"
            },
            "COUNTRY2": None,
            "OBJ1": None,
            "OBJ2": None
        }
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Origin": "https://www.worldgovernmentbonds.com",
        "Referer": "https://www.worldgovernmentbonds.com/country/vietnam/",
        "X-Requested-With": "XMLHttpRequest"
    }
    try:
        import requests
        from bs4 import BeautifulSoup
        
        response = requests.post(url, json=body, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            table_html = data.get('mainTable', '')
            if table_html:
                soup = BeautifulSoup(table_html, 'html.parser')
                for tr in soup.find_all('tr'):
                    tds = tr.find_all(['td', 'th'])
                    if len(tds) >= 3:
                        maturity = tds[1].text.strip().lower()
                        if "1 year" in maturity or maturity == "1y":
                            yield_str = tds[2].text.strip()
                            yield_str = yield_str.replace('%', '').replace(',', '').strip()
                            val = float(yield_str) / 100.0
                            if 0.01 < val < 0.15:  # Sanity check
                                return val
    except Exception:
        pass
    return 0.045  # Safe default fallback

# Standard Risk-Free Rate for Vietnamese Market (Default 4.5%, updated dynamically by orchestrator/pipelines)
RISK_FREE_RATE = 0.045

# ==========================================================
# 1. CORE BLACK-SCHOLES FORMULAS & GREEKS
# ==========================================

@njit
def calculate_d1_d2(S: float, K: float, T: float, r: float, sigma: float, q: float = 0.0) -> Tuple[float, float]:
    """Calculate d1 and d2 parameters for Black-Scholes formula with dividend yield q."""
    if T <= 0 or S <= 0 or K <= 0 or sigma <= 0:
        return 0.0, 0.0
    sqrt_T = math.sqrt(T)
    d1 = (math.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * sqrt_T)
    d2 = d1 - sigma * sqrt_T
    return d1, d2

@njit
def calculate_merton_jump_diffusion_price(S: float, K: float, T: float, r: float, sigma: float, 
                                          lamb: float, mu_J: float, sigma_J: float, 
                                          option_type_is_call: bool = True, max_n: int = 12, q: float = 0.0) -> float:
    """
    Merton's Jump-Diffusion Option Pricing Model with dividend yield q.
    Accounts for asset price jumps (fat tails) by adding a Poisson jump component.
    """
    if T <= 0 or S <= 0 or K <= 0 or sigma <= 0:
        return max(S - K, 0.0) if option_type_is_call else max(K - S, 0.0)
        
    kappa = math.exp(mu_J + 0.5 * sigma_J**2) - 1
    lamb_prime = lamb * (1 + kappa)
    
    price = 0.0
    fact = 1.0
    for n in range(max_n):
        if n > 0:
            fact *= n
        term_coef = math.exp(-lamb_prime * T) * ((lamb_prime * T)**n) / fact
        
        # Adjust drift for risk-free rate r and Poisson jump component (without subtracting q)
        r_n = r - lamb * kappa + (n * math.log(1 + kappa)) / T
        sigma_n = math.sqrt(sigma**2 + (n * sigma_J**2) / T)
        
        # Calculate BS price with dividend yield q
        d1, d2 = calculate_d1_d2(S, K, T, r_n, sigma_n, q)
        if option_type_is_call:
            bs_price = S * math.exp(-q * T) * n_cdf(d1) - K * math.exp(-r_n * T) * n_cdf(d2)
        else:
            bs_price = K * math.exp(-r_n * T) * n_cdf(-d2) - S * math.exp(-q * T) * n_cdf(-d1)
            
        price += term_coef * bs_price
        
    return float(price)

@njit
def calculate_delta(S: float, K: float, T: float, r: float, sigma: float, option_type_is_call: bool = True, q: float = 0.0) -> float:
    """Calculate Option Delta (Sensitivity to underlying asset price) with dividend yield q."""
    if T <= 0:
        if option_type_is_call:
            return 1.0 if S > K else 0.0
        return -1.0 if S < K else 0.0
    d1, _ = calculate_d1_d2(S, K, T, r, sigma, q)
    df_q = math.exp(-q * T)
    if option_type_is_call:
        return df_q * n_cdf(d1)
    return df_q * (n_cdf(d1) - 1.0)

@njit
def calculate_gamma(S: float, K: float, T: float, r: float, sigma: float, q: float = 0.0) -> float:
    """Calculate Option Gamma (Rate of change of Delta) with dividend yield q."""
    if T <= 0 or S <= 0 or sigma <= 0:
        return 0.0
    d1, _ = calculate_d1_d2(S, K, T, r, sigma, q)
    return math.exp(-q * T) * n_pdf(d1) / (S * sigma * math.sqrt(T))

@njit
def calculate_theta(S: float, K: float, T: float, r: float, sigma: float, option_type_is_call: bool = True, per_day: bool = True, q: float = 0.0) -> float:
    """Calculate Option Theta (Time decay per day) with dividend yield q."""
    if T <= 0 or S <= 0 or sigma <= 0:
        return 0.0
    d1, d2 = calculate_d1_d2(S, K, T, r, sigma, q)
    sqrt_T = math.sqrt(T)
    df_q = math.exp(-q * T)
    df_r = math.exp(-r * T)
    term1 = -(S * df_q * n_pdf(d1) * sigma) / (2.0 * sqrt_T)
    if option_type_is_call:
        theta = term1 + q * S * df_q * n_cdf(d1) - r * K * df_r * n_cdf(d2)
    else:
        theta = term1 - q * S * df_q * n_cdf(-d1) + r * K * df_r * n_cdf(-d2)
    if per_day:
        return theta / 365.0
    return theta

@njit
def calculate_vega(S: float, K: float, T: float, r: float, sigma: float, q: float = 0.0) -> float:
    """Calculate Option Vega (Sensitivity to a 1% absolute change in volatility) with dividend yield q."""
    if T <= 0 or S <= 0 or sigma <= 0:
        return 0.0
    d1, _ = calculate_d1_d2(S, K, T, r, sigma, q)
    return S * math.exp(-q * T) * n_pdf(d1) * math.sqrt(T) * 0.01

@njit
def calculate_rho(S: float, K: float, T: float, r: float, sigma: float, option_type_is_call: bool = True, q: float = 0.0) -> float:
    """Calculate Option Rho (Sensitivity to a 1% absolute change in risk-free interest rate) with dividend yield q."""
    if T <= 0 or S <= 0 or sigma <= 0:
        return 0.0
    _, d2 = calculate_d1_d2(S, K, T, r, sigma, q)
    df_r = math.exp(-r * T)
    if option_type_is_call:
        return K * T * df_r * n_cdf(d2) * 0.01
    return -K * T * df_r * n_cdf(-d2) * 0.01


def calculate_leland_volatility(sigma: float, spread_pct: float, k_transaction_cost: float = 0.0015, dt: float = 1.0/252.0, is_long: bool = True) -> float:
    """
    Calculate Leland's Liquidity-Adjusted Volatility to account for transaction costs and bid-ask spreads.
    spread_pct: Bid-Ask Spread in percentage (e.g. 2.5 for 2.5%)
    k_transaction_cost: Transaction cost rate (brokerage fee + taxes) (e.g. 0.0015 for 0.15%)
    dt: Hedging/rebalancing frequency in years (default: 1/252 for daily)
    is_long: True for option buyers (reduces volatility), False for writers/issuers.
    """
    if sigma <= 0 or dt <= 0:
        return sigma
    # Total transaction cost rate (one-way)
    k = k_transaction_cost + 0.5 * (spread_pct / 100.0)
    
    # Leland adjustment factor
    adjustment = np.sqrt(2.0 / np.pi) * k / (sigma * np.sqrt(dt))
    
    if is_long:
        # Long option buyers face higher transaction cost which dampens volatility
        variance_leland = sigma**2 * (1.0 - adjustment)
    else:
        variance_leland = sigma**2 * (1.0 + adjustment)
        
    if variance_leland <= 1e-4:
        return 0.01 # floor to prevent negative or zero volatility
    return float(np.sqrt(variance_leland))


def calculate_leland_price(S: float, K: float, T: float, r: float, sigma: float, spread_pct: float, 
                            option_type_is_call: bool = True, q: float = 0.0, k_transaction_cost: float = 0.0015, dt: float = 1.0/252.0) -> float:
    """
    Calculate Option Price using Leland's Liquidity-Adjusted BSM Model.
    """
    sigma_leland = calculate_leland_volatility(sigma, spread_pct, k_transaction_cost, dt, is_long=True)
    d1, d2 = calculate_d1_d2(S, K, T, r, sigma_leland, q)
    if option_type_is_call:
        price = S * np.exp(-q * T) * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    else:
        price = K * np.exp(-r * T) * norm.cdf(-d2) - S * np.exp(-q * T) * norm.cdf(-d1)
    return float(max(0.0, price))


def calculate_cbbc_bull_price(S: float, K: float, H: float, T: float, r: float, sigma: float, q: float = 0.0) -> float:
    """
    Down-and-out Call option pricing model (CBBC Bull contract)
    S: Spot Price
    K: Strike Price (usually K <= H)
    H: Call Price / Barrier (Knock-out level)
    """
    if S <= H:
        return 0.0 # Knocked out
    if T <= 0:
        return max(S - K, 0.0)
    
    # Standard BSM Call Price
    d1, d2 = calculate_d1_d2(S, K, T, r, sigma, q)
    bs_call = S * np.exp(-q * T) * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    
    # Down-and-In Call component
    sigma2 = sigma**2
    lam = (r - q + 0.5 * sigma2) / sigma2
    y = np.log(H**2 / (S * K)) / (sigma * np.sqrt(T)) + lam * sigma * np.sqrt(T)
    
    term_spot = S * np.exp(-q * T) * (H/S)**(2*lam) * norm.cdf(y)
    term_strike = K * np.exp(-r * T) * (H/S)**(2*lam - 2) * norm.cdf(y - sigma * np.sqrt(T))
    c_di = term_spot - term_strike
    
    price = bs_call - c_di
    return float(max(0.0, price))


def calculate_cbbc_bear_price(S: float, K: float, H: float, T: float, r: float, sigma: float, q: float = 0.0) -> float:
    """
    Up-and-out Put option pricing model (CBBC Bear contract)
    S: Spot Price
    K: Strike Price (usually K >= H)
    H: Call Price / Barrier (Knock-out level)
    """
    if S >= H:
        return 0.0 # Knocked out
    if T <= 0:
        return max(K - S, 0.0)
    
    # Standard BSM Put Price
    d1, d2 = calculate_d1_d2(S, K, T, r, sigma, q)
    bs_put = K * np.exp(-r * T) * norm.cdf(-d2) - S * np.exp(-q * T) * norm.cdf(-d1)
    
    # Up-and-In Put component
    sigma2 = sigma**2
    lam = (r - q + 0.5 * sigma2) / sigma2
    y = np.log(H**2 / (S * K)) / (sigma * np.sqrt(T)) + lam * sigma * np.sqrt(T)
    
    term_strike = K * np.exp(-r * T) * (H/S)**(2*lam - 2) * norm.cdf(-y + sigma * np.sqrt(T))
    term_spot = S * np.exp(-q * T) * (H/S)**(2*lam) * norm.cdf(-y)
    p_ui = term_strike - term_spot
    
    price = bs_put - p_ui
    return float(max(0.0, price))


def calculate_all_greeks(S: float, K: float, T: float, r: float, sigma: float, option_type: str = 'call', q: float = 0.0) -> Dict[str, float]:
    """Calculate all standard Greeks at once with dividend yield q."""
    is_call = option_type.lower() == 'call'
    return {
        'delta': calculate_delta(S, K, T, r, sigma, is_call, q),
        'gamma': calculate_gamma(S, K, T, r, sigma, q),
        'theta': calculate_theta(S, K, T, r, sigma, is_call, per_day=True, q=q),
        'vega': calculate_vega(S, K, T, r, sigma, q),
        'rho': calculate_rho(S, K, T, r, sigma, is_call, q)
    }

def calculate_greeks_for_cw(
    underlying_price: float,
    strike_price: float,
    days_to_maturity: int,
    implied_volatility: float,
    conversion_ratio: float = 1.0,
    risk_free_rate: float = RISK_FREE_RATE,
    option_type: str = 'call',
    q: float = 0.0
) -> Dict[str, Any]:
    """Calculate Greeks specifically for Vietnamese Covered Warrants, adjusting for conversion ratio and dividend yield q."""
    T = days_to_maturity / 365.0
    
    # Calculate moneyness
    moneyness = underlying_price / strike_price if strike_price > 0 else 0
    if moneyness > 1.05:
        moneyness_category = 'ITM'
    elif moneyness < 0.95:
        moneyness_category = 'OTM'
    else:
        moneyness_category = 'ATM'
        
    if T <= 0:
        prob_itm = 1.0 if underlying_price > strike_price else 0.0
        return {
            'delta': 1.0 if underlying_price > strike_price else 0.0,
            'gamma': 0.0, 'theta': 0.0, 'vega': 0.0, 'rho': 0.0,
            'moneyness': moneyness, 'moneyness_category': moneyness_category, 'prob_itm': prob_itm
        }
        
    # Calculate d1, d2
    _, d2 = calculate_d1_d2(underlying_price, strike_price, T, risk_free_rate, implied_volatility, q)
    is_call = option_type.lower() == 'call'
    prob_itm = float(n_cdf(d2)) if is_call else float(n_cdf(-d2))
    
    raw_greeks = calculate_all_greeks(underlying_price, strike_price, T, risk_free_rate, implied_volatility, option_type, q)
    greeks: Dict[str, Any] = dict(raw_greeks)
    
    # Adjust Greeks affected by the conversion ratio (Delta, Gamma, Vega are per unit)
    greeks['delta'] = greeks['delta'] / conversion_ratio
    greeks['gamma'] = greeks['gamma'] / conversion_ratio
    greeks['vega'] = greeks['vega'] / conversion_ratio
    
    # Append custom metrics
    greeks['moneyness'] = moneyness
    greeks['moneyness_category'] = moneyness_category
    greeks['prob_itm'] = prob_itm
    return greeks

# ==========================================
# 2. IMPLIED VOLATILITY NEWTON-RAPHSON SOLVER
# ==========================================

@njit
def _fast_iv_solver(
    market_price: float,
    underlying_price: float,
    strike_price: float,
    T: float,
    risk_free_rate: float,
    is_call: bool,
    max_iterations: int,
    tolerance: float,
    q: float = 0.0
) -> float:
    """Internal fast solver for IV with dividend yield q."""
    sigma = 0.3 # Initial volatility guess
    
    for _ in range(max_iterations):
        d1, d2 = calculate_d1_d2(underlying_price, strike_price, T, risk_free_rate, sigma, q)
        df_q = math.exp(-q * T)
        df_r = math.exp(-risk_free_rate * T)
        if is_call:
            price = (underlying_price * df_q * n_cdf(d1) - 
                     strike_price * df_r * n_cdf(d2))
        else:
            price = (strike_price * df_r * n_cdf(-d2) - 
                     underlying_price * df_q * n_cdf(-d1))
                     
        diff = market_price - price
        if abs(diff) < tolerance:
            return sigma
            
        vega = underlying_price * df_q * n_pdf(d1) * math.sqrt(T)
        if vega < 1e-10:
            break
            
        sigma = sigma + diff / vega
        sigma = max(0.01, min(sigma, 5.0)) # Bound checks
        
    return sigma

def estimate_implied_volatility(
    market_price: float,
    underlying_price: float,
    strike_price: float,
    days_to_maturity: int,
    risk_free_rate: float = RISK_FREE_RATE,
    option_type: str = 'call',
    max_iterations: int = 100,
    tolerance: float = 1e-5,
    q: float = 0.0
) -> float:
    """Solve for Implied Volatility (IV) using Newton-Raphson method with dividend yield q."""
    T = days_to_maturity / 365.0
    if T <= 0 or market_price <= 0:
        return 0.3
    
    is_call = option_type.lower() == 'call'
    return _fast_iv_solver(
        market_price, underlying_price, strike_price, T, 
        risk_free_rate, is_call, max_iterations, tolerance, q
    )

def parse_ratio(ratio_str: Any) -> float:
    """Safely parse exercise ratio strings such as '10:1' or '5:1' to numeric values."""
    if isinstance(ratio_str, (int, float)):
        return float(ratio_str)
    if not ratio_str:
        return 1.0
    try:
        ratio_s = str(ratio_str).strip()
        if ':' in ratio_s:
            parts = ratio_s.split(':')
            return float(parts[0]) / float(parts[1]) if len(parts) > 1 else float(parts[0])
        return float(ratio_s)
    except:
        return 1.0

# ==========================================
# 3. HARD GATES — ABSOLUTE DISQUALIFIERS
# ==========================================

# Bộ lọc cứng: Loại mã ngay lập tức bất kể G_Score cao đến đâu
# Tất cả ngưỡng đều có cơ sở định lượng rõ ràng
# Bộ lọc cứng (Đã được chuẩn hóa theo kinh nghiệm thực chiến của Pro-traders Việt Nam):
# Các ngưỡng này được siết chặt để loại bỏ hoàn toàn các mã "cờ bạc" và rủi ro cao.
HARD_GATES = {
    'min_days_to_expiry':     15,     # < 15 ngày: Cấm chơi.
    'min_gtgd_trieu':         50.0,   # Hạ từ 150tr xuống 50tr để bắt được các mã mới/cô đặc.
    'max_premium_pct':        18.0,   # Tiêu chí QUAN TRỌNG NHẤT.
    'max_iv_pct':            100.0,   
    'min_delta':               0.15,  
    'max_delta':               0.80,  
    'max_theta_burn_rate':     0.05,  
}

def passes_hard_gates(row: Any, use_derivatives_filter: bool = False) -> tuple:
    """
    Kiểm tra tất cả bộ lọc cứng. Đã tối ưu hóa cho thanh khoản thích ứng (Adaptive Liquidity).
    """
    # ... (Credit & Systemic checks remain the same)
    is_dist = int(row.get('underlying_is_distressed', 0) or 0)
    altman_z = float(row.get('underlying_altman_z', 3.0) or 3.0)
    if is_dist == 1 or altman_z < 1.1:
        return False, "DISTRESSED ASSET"

    sys_prob = float(row.get('underlying_systemic_prob', 0.10) or 0.10)
    if sys_prob >= 0.50:
        return False, f"SYSTEMIC RISK ({sys_prob:.0%})"

    # ── LỚP 0.1: Merton Structural Risk Gate (Real-time) ────────────────
    # Chặn các mã có rủi ro vỡ nợ cao dựa trên biến động giá & nợ
    underlying = str(row.get('S_CPCS', '') or '')
    current_stock_price = float(row.get('S_GiaCP', 0) or 0)
    
    if underlying and current_stock_price > 0:
        from src.modules.credit_risk.models.merton_engine import calculate_merton_dd_realtime
        merton = calculate_merton_dd_realtime(underlying, current_stock_price)
        if merton.get('status') == 'DISTRESSED':
            dd = merton.get('merton_dd', 0)
            return False, f"MERTON RISK (DD={dd:.2f})"

    # ── LỚP 0.5: Adaptive Liquidity & Spread Logic ────────────────────
    bid = float(row.get('bid', 0) or 0)
    ask = float(row.get('ask', 0) or 0)
    
    # Nếu cả bid VÀ ask đều = 0 -> Ngoài giờ giao dịch hoặc chưa có lệnh
    # Không tính là SPREAD RỘNG, coi như chưa có dữ liệu thực tế
    from datetime import datetime
    now = datetime.now()
    is_trading_hours = (now.hour == 9 or 
                        (10 <= now.hour < 15) or 
                        (now.hour == 15 and now.minute == 0))
    
    if bid > 0 and ask > 0:
        spread_pct = (ask - bid) / bid  # Spread thực sự có dữ liệu
    elif is_trading_hours and (bid > 0 or ask > 0):
        spread_pct = 0.50  # Một chiều lệnh trong giờ giao dịch -> spread rộng
    else:
        spread_pct = 0.0   # Ngoài giờ / không có lệnh -> bỏ qua spread check
    
    gtgd = float(row.get('E_GTGD', 0) or 0)
    hist_avg_gtgd = float(row.get('hist_avg_gtgd', 0.0) or 0.0)
    
    # CHIẾN LƯỢC: Nếu Spread cực hẹp (< 2%) -> Có MM xịn, chấp nhận GTGD thấp hơn (25tr)
    # Nếu Spread rộng -> Ép GTGD cao (50tr)
    min_gtgd_required = HARD_GATES['min_gtgd_trieu']
    if spread_pct < 0.02: # 2%
        min_gtgd_required = 25.0 # Chỉ cần 25tr/ngày nếu có MM kê lệnh sát
    
    # Buổi sáng (trước 10h) giảm 50% yêu cầu thanh khoản để bắt sóng
    if now.hour == 9 or (now.hour == 10 and now.minute < 30):
        min_gtgd_required *= 0.5

    if gtgd < min_gtgd_required and hist_avg_gtgd < min_gtgd_required:
        return False, f"THANH KHOẢN THẤP (Nay: {gtgd:.1f}tr, TB 10N: {hist_avg_gtgd:.1f}tr)"

    if spread_pct > 0.12: # Spread > 12% là quá rủi ro cho mọi trường hợp
        return False, f"SPREAD RỘNG ({spread_pct*100:.1f}%)"

    # ── LỚP 1: Các bộ lọc kỹ thuật khác ────────────────────────────────────
    sentiment = str(row.get('market_sentiment', 'NEUTRAL')).upper()
    max_premium_gate = HARD_GATES['max_premium_pct']
    min_days_gate = HARD_GATES['min_days_to_expiry']
    
    if use_derivatives_filter and sentiment == 'BEARISH':
        max_premium_gate = 12.0
        min_days_gate = 30

    # Extract required technical fields
    days       = float(row.get('L_Ngay', 0) or 0)
    premium    = float(row.get('Premium_Pct', 999) or 999)
    iv         = float(row.get('S_IV_Pct', 999) or 999)
    delta      = float(row.get('T_Delta', 0) or 0)
    cw_price   = float(row.get('C_GiaCW', 0) or 0)
    theta      = abs(float(row.get('T_Theta', 0) or 0))
    theta_burn = theta / cw_price if cw_price > 0 else 0

    if days < min_days_gate:
        reason = "ĐÁO HẠN NHANH" if sentiment != 'BEARISH' else "BÃO PHÁI SINH (ĐÁO HẠN < 30N)"
        return False, f"{reason} ({int(days)}N)"

    if premium > max_premium_gate:
        reason = "PREMIUM CAO" if sentiment != 'BEARISH' else "BÃO PHÁI SINH (PREMIUM CAO)"
        return False, f"{reason} ({premium:.0f}%)"
    if iv > HARD_GATES['max_iv_pct']:
        return False, f"IV CỰC CAO ({iv:.0f}%)"
    if delta < HARD_GATES['min_delta']:
        return False, f"DEEP OTM (Δ={delta:.2f})"
    if delta > HARD_GATES['max_delta']:
        return False, f"DEEP ITM (Δ={delta:.2f})"
    if theta_burn > HARD_GATES['max_theta_burn_rate']:
        return False, f"THETA BOMB ({theta_burn*100:.1f}%/ngày)"
    return True, ''

# ==========================================
# 3. SCORING & DECISION TREE ENGINES
# ==========================================

def score_cw(df: pd.DataFrame, strategy: str = 'balanced') -> pd.DataFrame:
    """
    Score Covered Warrants based on strategy (Safe, Balanced, Aggressive)
    using robust financial scaling (handling outliers in volume, gearing and upside).
    """
    res = df.copy()
    if res.empty:
        return res
        
    def normalize(series, reverse=False):
        if series.max() == series.min():
            return series * 0 + 50
        norm = (series - series.min()) / (series.max() - series.min()) * 100
        return 100 - norm if reverse else norm

    # Robust scaling for volume: use log1p transformation to handle log-normal distribution
    res['norm_vol'] = normalize(np.log1p(res['D_Volume']))
    
    # ── MM Liquidity & Spread integration ─────────────────────────────────
    if 'outstanding_volume' not in res.columns:
        res['outstanding_volume'] = 1000000.0
    else:
        res['outstanding_volume'] = res['outstanding_volume'].fillna(1000000.0)
        
    if 'Spread_Pct' not in res.columns:
        if 'bid' in res.columns and 'ask' in res.columns:
            b = res['bid'].astype(float).fillna(0)
            a = res['ask'].astype(float).fillna(0)
            res['Spread_Pct'] = np.where((b > 0) & (a > 0), (a - b) / b * 100, 0.0)
        else:
            res['Spread_Pct'] = 0.0
    else:
        res['Spread_Pct'] = res['Spread_Pct'].fillna(0.0)
        
    res['norm_outstanding'] = normalize(np.log1p(res['outstanding_volume']))
    res['norm_spread'] = normalize(res['Spread_Pct'].clip(0, 15), reverse=True)
    
    # Combine daily volume (50%), outstanding volume (30%), and bid-ask spread (20%)
    res['norm_vol'] = res['norm_vol'] * 0.5 + res['norm_outstanding'] * 0.3 + res['norm_spread'] * 0.2
    
    # Robust scaling for days to maturity: clip at 150 days (longer is great, no need to over-reward 300 days vs 150 days)
    res['norm_days'] = normalize(res['L_Ngay'].clip(0, 150))
    
    res['norm_prob'] = normalize(res['prob_itm'])
    
    # Robust scaling for gearing: clip at 15x (very high gearing is often too risky, 10x-15x is sweet)
    res['norm_gear'] = normalize(res['F_DonBay'].clip(0, 15))
    
    res['norm_iv'] = normalize(res['S_IV_Pct'], reverse=True)
    
    # Delta Sweet Spot (ATM optimization near 0.5)
    res['delta_score'] = res['T_Delta'].apply(lambda x: 100 - abs(x - 0.5) * 200).clip(0, 100)
    
    # 1. VALUATION DEPTH (LAV - Liquidity Adjusted Valuation)
    # The true upside must factor in the cost to cross the spread (Ask price)
    mkt_price = res['C_GiaCW'].astype(float)
    theo_price = res['theo_price'].astype(float)
    ask_col = res['ask'] if 'ask' in res.columns else mkt_price
    ask_price = ask_col.fillna(mkt_price).astype(float)
    
    # Use Leland theoretical price if available, otherwise fallback to BSM theo_price
    if 'theo_price_leland' in res.columns:
        theo_ref = np.where(res['theo_price_leland'] > 0, res['theo_price_leland'], theo_price)
    else:
        theo_ref = theo_price
        
    # Raw Upside (Mid-to-Theo) vs Real Upside (Ask-to-Theo) using Leland reference
    raw_upside = (theo_ref - mkt_price) / mkt_price.replace(0, np.nan)
    raw_upside = raw_upside.fillna(0)
    real_upside = (theo_ref - ask_price) / ask_price.replace(0, np.nan)
    real_upside = real_upside.fillna(0)
    
    # Penalize wide spreads in the valuation score
    bid_col = res['bid'] if 'bid' in res.columns else pd.Series(0.0, index=res.index)
    bid = bid_col.fillna(0).astype(float)
    spread_pct = (ask_price - bid) / bid.replace(0, np.nan)
    spread_pct = spread_pct.fillna(0.1)
    
    # Adjusted Upside Score (Institutional Grade)
    # We clip real_upside to remove outliers and normalize it
    clipped_upside = real_upside.clip(-0.5, 1.5)
    norm_upside = (clipped_upside + 0.5) / 2.0 * 100 # Map -50%..+150% to 0..100
    
    # 2. GREEK ALPHA & TIME DECAY
    # ... existing logic ...
    
    sentiment = 'NEUTRAL'
    if not res.empty and 'market_sentiment' in res.columns:
        sentiment = str(res['market_sentiment'].iloc[0]).upper()
 
    if strategy == 'safe':
        if sentiment == 'BEARISH':
            # Ultra-safe profile in a bear market: emphasize ITM probability (35%), expiry (30%), low IV (20%), reduce volume (10%), Delta (5%)
            res['G_Score'] = (res['norm_prob'] * 0.35 + res['norm_days'] * 0.30 + 
                              res['norm_iv'] * 0.20 + res['norm_vol'] * 0.10 + res['delta_score'] * 0.05)
        elif sentiment == 'BULLISH':
            # Slightly more opportunistic: ITM probability (25%), expiry (20%), low IV (10%), volume (15%), Gearing (20%), Delta (10%)
            res['G_Score'] = (res['norm_prob'] * 0.25 + res['norm_days'] * 0.20 + 
                              res['norm_iv'] * 0.10 + res['norm_vol'] * 0.15 + res['norm_gear'] * 0.20 + res['delta_score'] * 0.10)
        else:
            # Probability ITM (30%) + Days to expiry (25%) + Liquidity (20%) + Low IV (15%) + Delta Sweet (10%)
            res['G_Score'] = (res['norm_prob'] * 0.3 + res['norm_days'] * 0.25 + 
                              res['norm_vol'] * 0.2 + res['norm_iv'] * 0.15 + res['delta_score'] * 0.1)
    elif strategy == 'aggressive':
        if sentiment == 'BEARISH':
            # Defensive aggressive: Gearing (20%), Upside (25%), ITM probability (20%), Expiry (15%), Liquidity (10%), Delta (10%)
            res['G_Score'] = (res['norm_gear'] * 0.20 + norm_upside * 0.25 + 
                              res['norm_prob'] * 0.20 + res['norm_days'] * 0.15 + res['norm_vol'] * 0.10 + res['delta_score'] * 0.10)
        elif sentiment == 'BULLISH':
            # Aggressive bull mode: Gearing (40%), Upside (35%), Delta (15%), Liquidity (10%)
            base_score = (res['norm_gear'] * 0.40 + norm_upside * 0.35 + 
                          normalize(res['T_Delta']) * 0.15 + res['norm_vol'] * 0.10)
            
            # 🛡️ ANTI-SIDEWAYS PROTECTION (ADX Filter)
            # Penalize stocks that are not trending (ADX < 18 is dead sideways)
            def apply_trend_penalty(row):
                adx = row.get('underlying_adx', 25.0) # Assume trending if data missing
                if adx < 18: return 0.5 # Chop score in half for sideways death
                if adx < 22: return 0.8 # 20% penalty
                return 1.0
                
            res['G_Score'] = base_score * res.apply(apply_trend_penalty, axis=1)
        else:
            # Leverage Gearing (35%) + Fair Value Upside (30%) + Target Delta (20%) + Liquidity (15%)
            res['G_Score'] = (res['norm_gear'] * 0.35 + norm_upside * 0.3 + 
                              normalize(res['T_Delta']) * 0.2 + res['norm_vol'] * 0.15)
    else: # balanced
        if sentiment == 'BEARISH':
            # Balanced-safe in bear market: Delta Sweet (25%), Probability ITM (25%), Expiry (20%), Liquidity (15%), Upside (15%)
            res['G_Score'] = (res['delta_score'] * 0.25 + res['norm_prob'] * 0.25 + 
                              res['norm_days'] * 0.20 + res['norm_vol'] * 0.15 + norm_upside * 0.15)
        elif sentiment == 'BULLISH':
            # Balanced-aggressive in bull market: Delta Sweet (20%), Gearing (20%), Upside (25%), Liquidity (20%), Probability ITM (15%)
            res['G_Score'] = (res['delta_score'] * 0.20 + res['norm_gear'] * 0.20 + 
                              norm_upside * 0.25 + res['norm_vol'] * 0.20 + res['norm_prob'] * 0.15)
        else:
            # Delta Sweet (30%) + Liquidity (20%) + Probability ITM (20%) + Upside (20%) + Expiry (10%)
            res['G_Score'] = (res['delta_score'] * 0.3 + res['norm_vol'] * 0.2 + 
                              res['norm_prob'] * 0.2 + norm_upside * 0.2 + res['norm_days'] * 0.1)
        
    # Health score incorporates Fundamental FA score and Sentiment AI scores
    res['P_Health'] = (res['O_Stock_FA'] * 0.7 + (res.get('N_Sentiment', 0) * 50 + 50) * 0.3).clip(0, 100)
    return res
 
def make_decision(row: Any, use_derivatives_filter: bool = False) -> str:
    """
    Multi-layer decision engine cho giao dịch thực chiến.
 
    Lớp 1 — Hard Gates:     Loại ngay bất kể điểm số (an toàn tuyệt đối)
    Lớp 2 — Theta Bomb:     Cảnh báo hao mòn thời gian quá nhanh
    Lớp 3 — IV Signal:      Ưu tiên CW được định giá rẻ (IV < HV)
    Lớp 4 — Score Tiering:  Phân hạng khuyến nghị theo G_Score
    """
    # ── LỚP 1: Hard Gates — loại tức thì ────────────────────────────────────
    passed, reason = passes_hard_gates(row, use_derivatives_filter=use_derivatives_filter)
    if not passed:
        return f"SKIP ({reason})"
 
    # ── LỚP 2: Theta-Burn & Đáo hạn (Mô hình DVA thực chiến) ────────────────────────────
    cw_price = float(row.get('C_GiaCW', 0) or 0)
    theta    = abs(float(row.get('T_Theta', 0) or 0))
    theta_burn = theta / cw_price if cw_price > 0 else 0
    
    # Tính chi phí hao mòn 5 ngày (Theta Rent)
    theta_rent_5d = theta_burn * 5.0
    
    # Nếu chi phí hao mòn 5 ngày cắn quá 20% vốn, lập tức cảnh báo
    if theta_rent_5d > 0.20:
        return f"CAUTION (5D Θ-Rent={theta_rent_5d*100:.1f}%)"
 
    # ── LỚP 3: Volatility Arbitrage (Săn lệch giá biến động) ──────────────────────────
    # Check if we have GARCH volatility vs Implied Volatility
    # Use S_GARCH_Vol_Pct from ranker.py
    garch_vol_pct = float(row.get('S_GARCH_Vol_Pct', 0) or 0)
    iv_pct = float(row.get('S_IV_Pct', 0) or 0)
    
    vol_arb_bonus = False
    if garch_vol_pct > 0 and iv_pct > 0:
        # Nếu biến động dự báo (GARCH) lớn hơn biến động nhà cái đang áp giá (IV) > 15% -> Mỏ vàng!
        if garch_vol_pct - iv_pct > 15.0:
            vol_arb_bonus = True
            
    # GARCH Fair Value Upside
    garch_upside = float(row.get('I_GARCH_Upside', 0) or 0)
 
    # ── LỚP 3.5: MM Hedging Pressure Bonus ──────────────────────────────────────────
    delta = float(row.get('T_Delta', 0) or 0)
    outstanding_vol = float(row.get('outstanding_volume', 0) or 0)
    mm_pressure_bonus = False
    if delta > 0.6 and outstanding_vol > 5000000:
        mm_pressure_bonus = True
 
    iv_signal = str(row.get('IV_vs_HV_Signal', ''))
    score = float(row.get('G_Score', 0) or 0)
 
    # ── LỚP 4: Score Tiering ─────────────────────────────────────────────────
    cheap_bonus = 'CHEAP' in iv_signal  # Ưu tiên CW rẻ hơn HV
 
    if vol_arb_bonus and garch_upside > 0.2:
        return "VOL ARBITRAGE BUY" # Tín hiệu tấn công mạnh nhất
 
    if score >= 75 or (score >= 68 and (cheap_bonus or vol_arb_bonus)) or (score >= 70 and mm_pressure_bonus):
        return "STRONG BUY"
    if score >= 65 or (score >= 60 and (cheap_bonus or vol_arb_bonus)) or (score >= 60 and mm_pressure_bonus):
        return "BUY"
    if score >= 55:
        return "WATCH"
    return "SKIP"

def get_latest_merton_credit(ticker: str) -> Tuple[float, float]:
    """Retrieve distance to default and default probability from SQLite database."""
    try:
        from src.core.database import engine
        import pandas as pd
        query = f"SELECT distance_to_default, default_probability FROM corporate_merton_credit WHERE ticker = '{ticker}' ORDER BY date DESC LIMIT 1"
        res = pd.read_sql(query, engine)
        if not res.empty:
            return float(res['distance_to_default'].iloc[0]), float(res['default_probability'].iloc[0])
    except Exception:
        pass
    return None, None

def price_cw_with_credit_linkage(S: float, K: float, T: float, r: float, sigma: float, 
                                 underlying_symbol: str, option_type_is_call: bool = True, q: float = 0.0) -> Dict[str, Any]:
    """
    Prices a Covered Warrant by linking underlying Merton Structural Credit Risk.
    If the firm is distressed (PD > 1% or DD < 1.5), automatically switches to the
    Merton Jump-Diffusion model to account for sudden asset price drops.
    """
    dd, pd_val = get_latest_merton_credit(underlying_symbol)
    
    is_distressed = False
    model_used = 'BSM'
    price = 0.0
    
    if pd_val is not None and dd is not None:
        if pd_val > 0.01 or dd < 1.5:
            is_distressed = True
            model_used = 'Merton-Jump-Diffusion'
            
    if is_distressed:
        # Calibrate jump parameters based on distress severity
        severity = min(5.0, max(1.0, 1.5 / max(dd, 0.1)))
        lamb = 0.5 * severity      # jump frequency per year
        mu_J = -0.10 * severity     # average jump size (downward)
        sigma_J = 0.15 * severity   # jump volatility
        
        price = calculate_merton_jump_diffusion_price(
            S, K, T, r, sigma, lamb, mu_J, sigma_J, option_type_is_call, q=q
        )
    else:
        # Standard Black-Scholes
        d1, d2 = calculate_d1_d2(S, K, T, r, sigma, q)
        if option_type_is_call:
            price = S * math.exp(-q * T) * n_cdf(d1) - K * math.exp(-r * T) * n_cdf(d2)
        else:
            price = K * math.exp(-r * T) * n_cdf(-d2) - S * math.exp(-q * T) * n_cdf(-d1)
            
    return {
        'price': price,
        'model_used': model_used,
        'is_distressed': is_distressed,
        'distance_to_default': dd,
        'default_probability': pd_val
    }

