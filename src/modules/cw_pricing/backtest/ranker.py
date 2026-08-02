# -*- coding: utf-8 -*-
"""Greeks computation, IV solving, and scenario simulation for covered warrants."""

import numpy as np
import pandas as pd
from scipy.stats import norm

from src.modules.cw_pricing.models.pricing_core import (
    RISK_FREE_RATE,
    DEFAULT_VOLATILITY,
    calculate_d1_d2,
    calculate_greeks_for_cw,
    estimate_implied_volatility,
    parse_ratio,
    calculate_merton_jump_diffusion_price,
)

def fit_volatility_smile(df: pd.DataFrame) -> dict:
    """
    Fits a Volatility Smile curve (IV vs Moneyness) for each underlying stock
    using a robust polynomial regression (quadratic/degree 2) to smooth IV.
    Returns a dictionary mapping symbol to the smoothed/fitted IV.
    """
    fitted_iv_map = {}
    
    # Group warrants by underlying stock
    underlying_groups = df.groupby("B_MaCPCS")
    
    for underlying, group in underlying_groups:
        # Filter out rows with invalid market prices or extremely low IVs
        valid_group = group[
            (group["C_GiaCW"] > 0) & 
            (group["raw_iv"] > 0.05) & 
            (group["raw_iv"] < 2.0)
        ].copy()
        
        if len(valid_group) >= 3:
            # Fit a quadratic curve: IV = a * (S/K)^2 + b * (S/K) + c
            x = (valid_group["hidden_underlying_price"] / valid_group["R_Strike"]).values
            y = valid_group["raw_iv"].values
            
            try:
                poly_coefs = np.polyfit(x, y, deg=2)
                # For each warrant of this underlying (including OTM/ITM), estimate the fitted IV
                for idx, row in group.iterrows():
                    sym = row["A_MaCW"]
                    moneyness = row["hidden_underlying_price"] / row["R_Strike"]
                    fitted_iv = float(np.polyval(poly_coefs, moneyness))
                    fitted_iv = max(0.10, min(1.20, fitted_iv))
                    fitted_iv_map[sym] = fitted_iv
            except Exception:
                mean_iv = float(valid_group["raw_iv"].mean())
                for idx, row in group.iterrows():
                    fitted_iv_map[row["A_MaCW"]] = mean_iv
        elif len(valid_group) == 2:
            # Linear fit: IV = a * (S/K) + b
            x = (valid_group["hidden_underlying_price"] / valid_group["R_Strike"]).values
            y = valid_group["raw_iv"].values
            try:
                poly_coefs = np.polyfit(x, y, deg=1)
                for idx, row in group.iterrows():
                    sym = row["A_MaCW"]
                    moneyness = row["hidden_underlying_price"] / row["R_Strike"]
                    fitted_iv = float(np.polyval(poly_coefs, moneyness))
                    fitted_iv = max(0.10, min(1.20, fitted_iv))
                    fitted_iv_map[sym] = fitted_iv
            except Exception:
                mean_iv = float(valid_group["raw_iv"].mean())
                for idx, row in group.iterrows():
                    fitted_iv_map[row["A_MaCW"]] = mean_iv
        elif len(valid_group) == 1:
            mean_iv = float(valid_group["raw_iv"].iloc[0])
            for idx, row in group.iterrows():
                fitted_iv_map[row["A_MaCW"]] = mean_iv
        else:
            for idx, row in group.iterrows():
                fitted_iv_map[row["A_MaCW"]] = 0.40
                
    return fitted_iv_map


def run_quant_calculations(df: pd.DataFrame, hv_map: dict) -> pd.DataFrame:
    """Inject Greeks, Implied Volatility, Historical Volatility, and Black-Scholes valuations."""
    if df.empty:
        return df

    # Load GARCH forecast volatilities
    import os
    garch_vol_map = {}
    try:
        garch_path = os.path.join('data', 'processed', 'garch_vol_report.csv')
        if os.path.exists(garch_path):
            garch_df = pd.read_csv(garch_path)
            for _, r in garch_df.iterrows():
                garch_vol_map[r['symbol']] = float(r['garch_forecast_vol_pct']) / 100.0
    except Exception:
        pass
        
    # ── Fetch Derivatives Sentiment ──────────────────────────────────
    from src.modules.cw_pricing.backtest.fetcher import fetch_derivatives_sentiment
    sentiment_profile = fetch_derivatives_sentiment()
    sentiment = sentiment_profile.get('market_sentiment', 'NEUTRAL')
    basis = sentiment_profile.get('current_basis', 0.0)
    basis_sma5 = sentiment_profile.get('basis_sma5', 0.0)
    basis_mom = sentiment_profile.get('basis_momentum', 0.0)
    vol_spike = sentiment_profile.get('vol_spike_pct', 0.0)
    basis_z = sentiment_profile.get('basis_zscore', 0.0)
    
    res = df.copy()
    res['market_sentiment'] = sentiment
    res['current_basis'] = basis
    res['basis_sma5'] = basis_sma5
    res['basis_momentum'] = basis_mom
    res['vol_spike_pct'] = vol_spike
    res['basis_zscore'] = basis_z
    
    res['maturity_date_dt'] = pd.to_datetime(res['Q_DaoHan'], errors='coerce')
    res['days_to_expiry'] = (res['maturity_date_dt'] - pd.Timestamp.now()).dt.days
    res['L_Ngay'] = res['days_to_expiry']
    
    # Pass 1: Solve for raw implied volatilities
    raw_iv_list = []
    for idx, row in res.iterrows():
        try:
            S = float(row.get('hidden_underlying_price', 0) or 0)
            K = float(row.get('R_Strike', 0) or 0)
            days = float(row.get('days_to_expiry', 0) or 0)
            ratio = parse_ratio(row.get('hidden_ratio', '1:1'))
            m_price = float(row.get('C_GiaCW', 0) or 0)
            underlying_sym = row.get('B_MaCPCS')
            hv_dict = hv_map.get(underlying_sym, {'hv_40': 0.35})
            hv_40 = hv_dict.get('hv_40', 0.35)
            
            if S <= 0 or K <= 0 or days <= 0 or m_price <= 0:
                raw_iv_list.append(0.40)
                continue
                
            iv = estimate_implied_volatility(m_price * ratio, S, K, int(days), RISK_FREE_RATE)
            if iv <= 0.015:
                iv = max(hv_40, 0.10)
            raw_iv_list.append(iv)
        except Exception:
            raw_iv_list.append(0.40)
            
    res['raw_iv'] = raw_iv_list
    
    # Fit Volatility Smile
    fitted_iv_map = fit_volatility_smile(res)
    
    iv_list, delta_list, gamma_list, theta_list, vega_list, prob_list, theo_list, upside_list, theta_cw_list = [], [], [], [], [], [], [], [], []
    hv_10_list, hv_20_list, hv_40_list = [], [], []
    iv_vs_hv10_signal_list, iv_vs_hv20_signal_list, iv_vs_hv40_signal_list = [], [], []
    proj_3d_flat_list, proj_3d_up_list, proj_3d_down_list = [], [], []
    garch_vol_list, theo_garch_list, upside_garch_list = [], [], []
    theo_merton_list, upside_merton_list = [], []
    
    for idx, row in res.iterrows():
        try:
            S = float(row.get('hidden_underlying_price', 0) or 0)
            K = float(row.get('R_Strike', 0) or 0)
            days = float(row.get('days_to_expiry', 0) or 0)
            ratio = parse_ratio(row.get('hidden_ratio', '1:1'))
            m_price = float(row.get('C_GiaCW', 0) or 0)
            symbol = row.get('A_MaCW')
            
            underlying_sym = row.get('B_MaCPCS')
            hv_dict = hv_map.get(underlying_sym, {'hv_10': 0.35, 'hv_20': 0.35, 'hv_40': 0.35})
            hv_10 = hv_dict.get('hv_10', 0.35)
            hv_20 = hv_dict.get('hv_20', 0.35)
            hv_40 = hv_dict.get('hv_40', 0.35)
            
            if S <= 0 or K <= 0 or days <= 0 or m_price <= 0:
                iv_list.append(0.3); delta_list.append(0.0); gamma_list.append(0.0); theta_list.append(0.0); vega_list.append(0.0); prob_list.append(0.0); theo_list.append(0.0); upside_list.append(0.0)
                theta_cw_list.append(0.0)
                hv_10_list.append(0.35); hv_20_list.append(0.35); hv_40_list.append(0.35)
                iv_vs_hv10_signal_list.append('FAIR'); iv_vs_hv20_signal_list.append('FAIR'); iv_vs_hv40_signal_list.append('FAIR')
                proj_3d_flat_list.append(0.0); proj_3d_up_list.append(0.0); proj_3d_down_list.append(0.0)
                garch_vol_list.append(0.35); theo_garch_list.append(0.0); upside_garch_list.append(0.0)
                theo_merton_list.append(0.0); upside_merton_list.append(0.0)
                continue
                
            # Retrieve the smoothed IV from the Volatility Smile curve
            iv = fitted_iv_map.get(symbol, row['raw_iv'])
            
            # 2. Compute Greeks using the smoothed Volatility Smile IV
            greeks = calculate_greeks_for_cw(S, K, int(days), iv, ratio, RISK_FREE_RATE)
            
            # 3. Compute Theoretical Fair Value (using the smoothed Volatility Smile IV instead of static default)
            T = days / 365.0
            d1, d2 = calculate_d1_d2(S, K, T, RISK_FREE_RATE, iv)
            theo_price = (S * norm.cdf(d1) - K * np.exp(-RISK_FREE_RATE * T) * norm.cdf(d2)) / ratio
            
            # Retrieve the GARCH volatility for this underlying
            garch_vol = garch_vol_map.get(underlying_sym, hv_40)
            
            # Compute GARCH theoretical price
            d1_garch, d2_garch = calculate_d1_d2(S, K, T, RISK_FREE_RATE, garch_vol)
            theo_price_garch = (S * norm.cdf(d1_garch) - K * np.exp(-RISK_FREE_RATE * T) * norm.cdf(d2_garch)) / ratio
            upside_garch = (theo_price_garch - m_price) / m_price if m_price > 0 else 0
            
            # Compute Merton Jump-Diffusion theoretical price (using standard parameters: lambda=1.0, mu_J=-0.05, sigma_J=0.15)
            theo_price_merton = calculate_merton_jump_diffusion_price(S, K, T, RISK_FREE_RATE, iv, lamb=1.0, mu_J=-0.05, sigma_J=0.15) / ratio
            upside_merton = (theo_price_merton - m_price) / m_price if m_price > 0 else 0

            # 4. Volatility Arbitrage Signals across three windows
            def get_vol_sig(v_iv, v_hv):
                if v_iv < v_hv - 0.05:
                    return 'CHEAP'
                elif v_iv > v_hv + 0.10:
                    return 'EXPENSIVE'
                return 'FAIR'
                
            vol_sig_10 = get_vol_sig(iv, hv_10)
            vol_sig_20 = get_vol_sig(iv, hv_20)
            vol_sig_40 = get_vol_sig(iv, hv_40)
                
            # 5. Compute 3-Day Projected Prices & Returns (T+3 Forecast under flat, bullish, bearish paths)
            days_3d = max(days - 3, 0)
            
            def get_proj_price(S_target):
                if days_3d <= 0 or S_target <= 0 or iv <= 0:
                    return max(S_target - K, 0.0) / ratio
                T_3d = days_3d / 365.0
                try:
                    d1_3d, d2_3d = calculate_d1_d2(S_target, K, T_3d, RISK_FREE_RATE, iv)
                    return (S_target * norm.cdf(d1_3d) - K * np.exp(-RISK_FREE_RATE * T_3d) * norm.cdf(d2_3d)) / ratio
                except Exception:
                    return max(S_target - K, 0.0) / ratio
                    
            p_flat = get_proj_price(S)
            p_up = get_proj_price(S * 1.02)     # +2% underlying movement
            p_down = get_proj_price(S * 0.98)   # -2% underlying movement
            
            ret_flat = (p_flat - m_price) / m_price * 100 if m_price > 0 else 0
            ret_up = (p_up - m_price) / m_price * 100 if m_price > 0 else 0
            ret_down = (p_down - m_price) / m_price * 100 if m_price > 0 else 0
            
            iv_list.append(iv)
            delta_list.append(greeks['delta'])
            gamma_list.append(greeks['gamma'])
            theta_list.append(greeks['theta'])
            vega_list.append(greeks['vega'])
            prob_list.append(greeks['prob_itm'])
            theo_list.append(theo_price)
            upside_list.append((theo_price - m_price) / m_price if m_price > 0 else 0)
            theta_cw_list.append(greeks['theta'] / ratio)
            
            hv_10_list.append(hv_10)
            hv_20_list.append(hv_20)
            hv_40_list.append(hv_40)
            
            iv_vs_hv10_signal_list.append(vol_sig_10)
            iv_vs_hv20_signal_list.append(vol_sig_20)
            iv_vs_hv40_signal_list.append(vol_sig_40)
            
            proj_3d_flat_list.append(ret_flat)
            proj_3d_up_list.append(ret_up)
            proj_3d_down_list.append(ret_down)
            
            garch_vol_list.append(garch_vol)
            theo_garch_list.append(theo_price_garch)
            upside_garch_list.append(upside_garch)
            theo_merton_list.append(theo_price_merton)
            upside_merton_list.append(upside_merton)
            
        except Exception:
            iv_list.append(0.3); delta_list.append(0.0); gamma_list.append(0.0); theta_list.append(0.0); vega_list.append(0.0); prob_list.append(0.0); theo_list.append(0.0); upside_list.append(0.0); theta_cw_list.append(0.0)
            hv_10_list.append(0.35); hv_20_list.append(0.35); hv_40_list.append(0.35)
            iv_vs_hv10_signal_list.append('FAIR'); iv_vs_hv20_signal_list.append('FAIR'); iv_vs_hv40_signal_list.append('FAIR')
            proj_3d_flat_list.append(0.0); proj_3d_up_list.append(0.0); proj_3d_down_list.append(0.0)
            garch_vol_list.append(0.35); theo_garch_list.append(0.0); upside_garch_list.append(0.0)
            theo_merton_list.append(0.0); upside_merton_list.append(0.0)
            
    res['S_IV_Pct'] = np.array(iv_list) * 100
    res['S_HV_10_Pct'] = np.array(hv_10_list) * 100
    res['S_HV_20_Pct'] = np.array(hv_20_list) * 100
    res['S_HV_40_Pct'] = np.array(hv_40_list) * 100
    res['S_HV_Pct'] = res['S_HV_40_Pct']  # Backward compatibility alias
    res['S_GARCH_Vol_Pct'] = np.array(garch_vol_list) * 100
    res['IV_vs_HV10_Signal'] = iv_vs_hv10_signal_list
    res['IV_vs_HV20_Signal'] = iv_vs_hv20_signal_list
    res['IV_vs_HV_Signal'] = iv_vs_hv40_signal_list  # Backward compatibility
    res['T_Delta'] = delta_list
    res['T_Gamma'] = gamma_list
    res['T_Theta'] = theta_cw_list   # VND suy hao/ngày trên mỗi CW (đồng)
    res['T_Vega'] = vega_list
    res['prob_itm'] = prob_list
    res['theo_price'] = theo_list
    res['theo_price_garch'] = theo_garch_list
    res['theo_price_merton'] = theo_merton_list
    res['I_Upside'] = upside_list
    res['I_GARCH_Upside'] = upside_garch_list
    res['I_Merton_Upside'] = upside_merton_list
    res['proj_3d_flat_pct'] = proj_3d_flat_list
    res['proj_3d_up_pct'] = proj_3d_up_list
    res['proj_3d_down_pct'] = proj_3d_down_list
    def _moneyness(r):
        S = float(r.get('hidden_underlying_price', 0) or 0)
        K = float(r.get('R_Strike', 0) or 0)
        if K <= 0 or S <= 0:
            return 'OTM'
        m = S / K
        if m < 0.85:
            return 'DEEP OTM'   # S lỗ > 15% so với Strike → Chắc chắn SKIP
        elif m < 0.98:
            return 'OTM'        # Lỗ nhẹ, đòn bẩy thô cao nhưng rủi ro
        elif m <= 1.02:
            return 'ATM'        # Vùng nổ Vol, Gamma max, nhạy sóng nhất
        elif m <= 1.15:
            return 'ITM'        # Đã có lãi, an toàn cho profile Balanced
        else:
            return 'DEEP ITM'   # Lãi sâu > 15%, Delta ~ 1, chạy như cổ phiếu cơ sở
    res['K_ITM_OTM'] = res.apply(_moneyness, axis=1)
    
    res['H_Loai'] = 'Call'
    res['M_GiaHL'] = res['R_Strike'] + (res['C_GiaCW'] * res['hidden_ratio'].apply(parse_ratio))
    res['J_HoaVon'] = res.apply(lambda r: (r['M_GiaHL'] - r['hidden_underlying_price'])/r['hidden_underlying_price'] if r.get('hidden_underlying_price', 0) > 0 else 0, axis=1)
    res['Premium_Pct'] = res['J_HoaVon'] * 100
    
    # 3 Cột nâng cấp khớp 100% với screenshot của "Họ" và được giải mã thuật toán tối ưu:
    res['price_change_pct'] = res.apply(lambda r: ((r['C_GiaCW'] - r['ref_price']) / r['ref_price'] * 100) if r['ref_price'] > 0 else 0, axis=1)
    res['intrinsic_value'] = res.apply(lambda r: max(0.0, (r['hidden_underlying_price'] - r['R_Strike']) / parse_ratio(r['hidden_ratio'])), axis=1)
    res['risk_monthly_pct'] = res.apply(lambda r: (r['Premium_Pct'] / (r['L_Ngay'] / 30.0)) if r['L_Ngay'] > 0 else 0, axis=1)
    
    # Calculate Bid-Ask Spread percentage
    def _spread_pct(r):
        b = float(r.get('bid', 0) or 0)
        a = float(r.get('ask', 0) or 0)
        if b > 0 and a > 0:
            return (a - b) / b * 100
        return 0.0
    res['Spread_Pct'] = res.apply(_spread_pct, axis=1)
    
    # Calculate Gearing
    res['F_DonBay'] = res.apply(lambda r: (r['T_Delta'] * r['hidden_underlying_price'] / r['C_GiaCW']) if r['C_GiaCW'] > 0 and r.get('hidden_underlying_price', 0) > 0 else 0, axis=1)
    
    return res

def simulate_cw_scenarios(row):
    """
    Generate and print a 2D P/L Scenario Matrix for a specific Covered Warrant.
    X-axis: Underlying Stock price change (-10% to +10%)
    Y-axis: Time decay / Holding period (0 to 30 days)
    """
    symbol = row['A_MaCW']
    S = float(row.get('hidden_underlying_price', 0) or 0)
    K = float(row.get('R_Strike', 0) or 0)
    days_to_maturity = int(row.get('L_Ngay', 0) or 0)
    iv = float(row.get('S_IV_Pct', 45) or 45) / 100.0
    ratio = parse_ratio(row.get('hidden_ratio', '1:1'))
    current_price = float(row.get('C_GiaCW', 0) or 0)
    underlying_symbol = row['B_MaCPCS']
    
    if S <= 0 or current_price <= 0:
        print(f"❌ Invalid underlying price or warrant price for {symbol}.")
        return

    print("\n" + "=" * 125)
    print(f" 📊 VN-QUANT SCENARIO SIMULATOR: {symbol} (Underlying: {underlying_symbol})")
    print(f" Strike: {K:,.0f}đ | current Price: {current_price:,.0f}đ | IV: {iv*100:.2f}% | Days to Expiry: {days_to_maturity} days")
    print("=" * 125)
    print("📌 Expected P/L (%) based on holding period & stock price change (European Black-Scholes pricing):")
    print("=" * 125)
    
    # Scenarios
    price_changes = [-0.10, -0.05, -0.02, 0.00, 0.02, 0.05, 0.10]
    holding_days = [0, 5, 10, 20, 30]
    
    # Columns header
    headers = [f"{chg*100:+.0f}% ({S * (1+chg):,.0f}đ)" for chg in price_changes]
    print(f"{'Holding Period':<15} | " + " | ".join(f"{h:>14}" for h in headers))
    print("-" * 125)
    
    for hold in holding_days:
        if hold >= days_to_maturity:
            continue
            
        remaining_days = days_to_maturity - hold
        T_new = remaining_days / 365.0
        
        row_str = f"Sau {hold:<2} ngày"
        row_cells = []
        
        for chg in price_changes:
            S_new = S * (1 + chg)
            
            # Recalculate BSM
            d1, d2 = calculate_d1_d2(S_new, K, T_new, RISK_FREE_RATE, iv)
            theo_new = (S_new * norm.cdf(d1) - K * np.exp(-RISK_FREE_RATE * T_new) * norm.cdf(d2)) / ratio
            
            # P/L
            pl_pct = (theo_new - current_price) / current_price * 100
            
            # Format cell
            if pl_pct >= 0:
                cell_str = f"+{pl_pct:.1f}%"
            else:
                cell_str = f"{pl_pct:.1f}%"
                
            row_cells.append(f"{cell_str:>14}")
            
        print(f"{row_str:<15} | " + " | ".join(row_cells))
        
    print("=" * 125)
    print("💡 Tip: Holding period models Theta decay. +% Underlying represents positive Delta movement.")
    print("=" * 125 + "\n")
