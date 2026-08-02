# -*- coding: utf-8 -*-
"""CSV export, SQLite sync, Telegram alerts, and CLI terminal reporting."""

import os
import sys
import pandas as pd
from datetime import datetime

REPORT_PATH = os.path.join('data', 'processed', 'excel_cw_report.csv')


def export_csv(df: pd.DataFrame, path: str = REPORT_PATH) -> str:
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    df.to_csv(path, index=False)
    print(f'💾 Analysis complete! Full dataset exported successfully to {path}')
    return path


def save_opportunities_to_db(df: pd.DataFrame):
    """Persist quantitative scan results to SQLite Database (market_opportunities table)."""
    try:
        from src.core.database import SessionLocal, MarketOpportunity
        from datetime import datetime, timezone
        
        db = SessionLocal()
        try:
            # Clear existing table to perform full reload
            db.query(MarketOpportunity).delete()
            
            for _, row in df.iterrows():
                symbol = str(row.get('A_MaCW', '')).strip().upper()
                if not symbol:
                    continue
                
                opp = MarketOpportunity(
                    symbol=symbol,
                    underlying=row.get('B_MaCPCS'),
                    issuer=row.get('issuer'),
                    price=float(row.get('C_GiaCW', 0.0)) if pd.notna(row.get('C_GiaCW')) else None,
                    price_change_pct=float(row.get('price_change_pct', 0.0)) if pd.notna(row.get('price_change_pct')) else None,
                    intrinsic_value=float(row.get('intrinsic_value', 0.0)) if pd.notna(row.get('intrinsic_value')) else None,
                    break_even_price=float(row.get('M_GiaHL', 0.0)) if pd.notna(row.get('M_GiaHL')) else None,
                    premium_pct=float(row.get('Premium_Pct', 0.0)) if pd.notna(row.get('Premium_Pct')) else None,
                    risk_monthly_pct=float(row.get('risk_monthly_pct', 0.0)) if pd.notna(row.get('risk_monthly_pct')) else None,
                    gearing=float(row.get('F_DonBay', 0.0)) if pd.notna(row.get('F_DonBay')) else None,
                    days_to_maturity=int(row.get('L_Ngay', 0)) if pd.notna(row.get('L_Ngay')) else None,
                    score=float(row.get('G_Score', 0.0)) if pd.notna(row.get('G_Score')) else None,
                    decision_signal=row.get('U_Signal'),
                    
                    underlying_price=float(row.get('hidden_underlying_price', 0.0)) if pd.notna(row.get('hidden_underlying_price')) else None,
                    ratio=str(row.get('hidden_ratio', '1:1')),
                    strike_price=float(row.get('R_Strike', 0.0)) if pd.notna(row.get('R_Strike')) else None,
                    volume=float(row.get('D_Volume', 0.0)) if pd.notna(row.get('D_Volume')) else None,
                    turnover=float(row.get('E_GTGD', 0.0)) if pd.notna(row.get('E_GTGD')) else None,
                    implied_volatility_pct=float(row.get('S_IV_Pct', 0.0)) if pd.notna(row.get('S_IV_Pct')) else None,
                    historical_volatility_pct=float(row.get('S_HV_Pct', 0.0)) if pd.notna(row.get('S_HV_Pct')) else None,
                    delta=float(row.get('T_Delta', 0.0)) if pd.notna(row.get('T_Delta')) else None,
                    gamma=float(row.get('T_Gamma', 0.0)) if pd.notna(row.get('T_Gamma')) else None,
                    theta_burn_day=float(row.get('T_Theta', 0.0)) if pd.notna(row.get('T_Theta')) else None,
                    vega=float(row.get('T_Vega', 0.0)) if pd.notna(row.get('T_Vega')) else None,
                    prob_itm=float(row.get('prob_itm', 0.0)) if pd.notna(row.get('prob_itm')) else None,
                    theoretical_price=float(row.get('theo_price', 0.0)) if pd.notna(row.get('theo_price')) else None,
                    upside_pct=float(row.get('I_Upside', 0.0)) if pd.notna(row.get('I_Upside')) else None,
                    garch_theoretical_price=float(row.get('theo_price_garch', 0.0)) if pd.notna(row.get('theo_price_garch')) else None,
                    garch_upside_pct=float(row.get('I_GARCH_Upside', 0.0)) if pd.notna(row.get('I_GARCH_Upside')) else None,
                    merton_theoretical_price=float(row.get('theo_price_merton', 0.0)) if pd.notna(row.get('theo_price_merton')) else None,
                    merton_upside_pct=float(row.get('I_Merton_Upside', 0.0)) if pd.notna(row.get('I_Merton_Upside')) else None,
                    proj_3d_flat_pct=float(row.get('proj_3d_flat_pct', 0.0)) if pd.notna(row.get('proj_3d_flat_pct')) else None,
                    proj_3d_up_pct=float(row.get('proj_3d_up_pct', 0.0)) if pd.notna(row.get('proj_3d_up_pct')) else None,
                    proj_3d_down_pct=float(row.get('proj_3d_down_pct', 0.0)) if pd.notna(row.get('proj_3d_down_pct')) else None,
                    moneyness_category=row.get('K_ITM_OTM'),
                    
                    underlying_distress_prob=float(row.get('underlying_distress_prob', 0.0)) if pd.notna(row.get('underlying_distress_prob')) else None,
                    underlying_is_distressed=int(row.get('underlying_is_distressed', 0)) if pd.notna(row.get('underlying_is_distressed')) else None,
                    underlying_altman_z=float(row.get('underlying_altman_z', 3.0)) if pd.notna(row.get('underlying_altman_z')) else None,
                    # DebtRank Network Contagion Risk
                    underlying_systemic_prob=float(row.get('underlying_systemic_prob', 0.10)) if pd.notna(row.get('underlying_systemic_prob')) else None,
                    underlying_systemic_delta=float(row.get('underlying_systemic_delta', 0.0)) if pd.notna(row.get('underlying_systemic_delta')) else None,
                    underlying_systemic_is_distressed=int(row.get('underlying_systemic_is_distressed', 0)) if pd.notna(row.get('underlying_systemic_is_distressed')) else None,
                    
                    # Banking specific health metrics (CAMELS-lite)
                    underlying_nim=float(row.get('underlying_nim', 0.0)) if pd.notna(row.get('underlying_nim')) else None,
                    underlying_npl=float(row.get('underlying_npl', 0.0)) if pd.notna(row.get('underlying_npl')) else None,
                    underlying_casa=float(row.get('underlying_casa', 0.0)) if pd.notna(row.get('underlying_casa')) else None,
                    underlying_car=float(row.get('underlying_car', 0.0)) if pd.notna(row.get('underlying_car')) else None,
                    
                    last_updated=datetime.now(timezone.utc)
                )
                db.add(opp)
            db.commit()
            print("🚀 Successfully synchronized pricing opportunities to finvista.db!")
        except Exception as e:
            db.rollback()
            print(f"⚠️ Failed to save opportunities to SQLite: {e}")
        finally:
            db.close()
    except Exception as e:
         print(f"⚠️ Database import error in run_analysis: {e}")


def print_terminal_report(final_df, args):
    # Extract derivatives sentiment metrics
    sentiment = "NEUTRAL"
    basis = 0.0
    basis_sma5 = 0.0
    basis_mom = 0.0
    vol_spike = 0.0
    basis_z = 0.0
    if not final_df.empty and 'market_sentiment' in final_df.columns:
        first_row = final_df.iloc[0]
        sentiment = str(first_row.get('market_sentiment', 'NEUTRAL')).upper()
        basis = float(first_row.get('current_basis', 0.0))
        basis_sma5 = float(first_row.get('basis_sma5', 0.0))
        basis_mom = float(first_row.get('basis_momentum', 0.0))
        vol_spike = float(first_row.get('vol_spike_pct', 0.0))
        basis_z = float(first_row.get('basis_zscore', 0.0))
        
    print("\n" + "=" * 145)
    print(" 📊 VN30F1M DERIVATIVES MARKET SENTIMENT PROFILE")
    print("=" * 145)
    sent_indicator = "🟢 BULLISH" if sentiment == 'BULLISH' else "🔴 BEARISH" if sentiment == 'BEARISH' else "🟡 NEUTRAL"
    print(f"  Trạng thái: {sent_indicator:<10} |  Basis hiện tại: {basis:>+5.2f} |  Basis SMA5: {basis_sma5:>+5.2f} |  Đà Basis: {basis_mom:>+5.2f} |  Basis Z-Score: {basis_z:>+5.2f} |  Đột biến KL Phái sinh: {vol_spike:>+5.1f}%")
    print("=" * 145)

    # Calculate market breadth metrics
    active_df = final_df[final_df['C_GiaCW'] > 0]
    up_cnt = len(active_df[active_df['C_GiaCW'] > active_df['ref_price']])
    down_cnt = len(active_df[active_df['C_GiaCW'] < active_df['ref_price']])
    flat_cnt = len(active_df[active_df['C_GiaCW'] == active_df['ref_price']])
    total_cnt = len(final_df)
    print("\n" + "=" * 145)
    print(" 📡 THỐNG KÊ TOÀN CẢNH ĐỘ RỘNG THỊ TRƯỜNG CHỨNG QUYỀN (Market Breadth)")
    print("=" * 145)
    print(f"  Tổng số mã quét: {total_cnt:<3} |  📈 Tăng giá: {up_cnt:<3} |  📉 Giảm giá: {down_cnt:<3} |  ➖ Tham chiếu: {flat_cnt:<3}")
    print("=" * 145)
    
    # Determine limits
    display_limit = len(final_df) if args.all else args.limit
    
    master_cols = {
        'A_MaCW': 'Mã CW',
        'B_MaCPCS': 'Mã CPCS',
        'issuer': 'TCPH',
        'C_GiaCW': 'Giá CW',
        'price_change_pct': '+/- (%)',
        'Spread_Pct': 'Spread',
        'hidden_underlying_price': 'Giá Cơ Sở',
        'Premium_Pct': 'Premium',
        'D_Volume': 'KLGD',
        'S_IV_Pct': 'IV',
        'S_HV_Pct': 'HV',
        'T_Delta': 'Delta',
        'F_DonBay': 'Đòn Bẩy',
        'L_Ngay': 'Đáo Hạn',
        'G_Score': 'Điểm',
        'U_Signal': 'Khuyến Nghị'
    }
    
    # Slice the top N warrants for display
    top_df = final_df.head(display_limit).copy()
    
    if args.group_by:
        group_col = 'B_MaCPCS' if args.group_by == 'cpcs' else 'issuer'
        group_label = 'CỔ PHIẾU CƠ SỞ (CPCS)' if args.group_by == 'cpcs' else 'NHÀ PHÁT HÀNH (TCPH)'
        
        print("\n" + "=" * 145)
        print(f" 🏆 VN-QUANT: PHÂN TÍCH NHÓM THEO {group_label}")
        print("=" * 145)
        
        # Group by and print
        grouped = top_df.groupby(group_col, sort=True)
        for g_name, g_df in grouped:
            if g_df.empty:
                continue
                
            clean_g_name = g_name if g_name else "Không xác định"
            print(f"\n📂 Nhóm: {clean_g_name} ({len(g_df)} mã cơ hội)")
            print("-" * 145)
            
            table_df = g_df[list(master_cols.keys())].copy()
            table_df['C_GiaCW'] = table_df['C_GiaCW'].map('{:,.0f}đ'.format)
            table_df['price_change_pct'] = table_df['price_change_pct'].map('{:+.1f}%'.format)
            table_df['Spread_Pct'] = table_df['Spread_Pct'].map('{:.1f}%'.format)
            table_df['hidden_underlying_price'] = table_df['hidden_underlying_price'].map('{:,.0f}đ'.format)
            table_df['Premium_Pct'] = table_df['Premium_Pct'].map('{:+.1f}%'.format)
            table_df['D_Volume'] = table_df['D_Volume'].map('{:,.0f}'.format)
            table_df['S_IV_Pct'] = table_df['S_IV_Pct'].map('{:.1f}%'.format)
            table_df['S_HV_Pct'] = table_df['S_HV_Pct'].map('{:.1f}%'.format)
            table_df['T_Delta'] = table_df['T_Delta'].map('{:.2f}'.format)
            table_df['F_DonBay'] = table_df['F_DonBay'].map('{:.1f}x'.format)
            table_df['L_Ngay'] = table_df['L_Ngay'].map('{:.0f}N'.format)
            table_df['G_Score'] = table_df['G_Score'].map('{:.1f}'.format)
            
            table_df = table_df.rename(columns=master_cols)
            if args.group_by == 'cpcs':
                table_df = table_df.drop(columns=['Mã CPCS'], errors='ignore')
            elif args.group_by == 'tcph':
                table_df = table_df.drop(columns=['TCPH'], errors='ignore')
            print(table_df.to_string(index=False))
            print("-" * 145)
            
    else:
        # Standard list representation
        print("\n" + "=" * 145)
        print(f" 🏆 TOP {display_limit} COVERED WARRANT OPPORTUNITIES (Vietnam Live Market)")
        print("=" * 145)
        
        table_df = top_df[list(master_cols.keys())].copy()
        table_df['C_GiaCW'] = table_df['C_GiaCW'].map('{:,.0f}đ'.format)
        table_df['price_change_pct'] = table_df['price_change_pct'].map('{:+.1f}%'.format)
        table_df['Spread_Pct'] = table_df['Spread_Pct'].map('{:.1f}%'.format)
        table_df['hidden_underlying_price'] = table_df['hidden_underlying_price'].map('{:,.0f}đ'.format)
        table_df['Premium_Pct'] = table_df['Premium_Pct'].map('{:+.1f}%'.format)
        table_df['D_Volume'] = table_df['D_Volume'].map('{:,.0f}'.format)
        table_df['S_IV_Pct'] = table_df['S_IV_Pct'].map('{:.1f}%'.format)
        table_df['S_HV_Pct'] = table_df['S_HV_Pct'].map('{:.1f}%'.format)
        table_df['T_Delta'] = table_df['T_Delta'].map('{:.2f}'.format)
        table_df['F_DonBay'] = table_df['F_DonBay'].map('{:.1f}x'.format)
        table_df['L_Ngay'] = table_df['L_Ngay'].map('{:.0f}N'.format)
        table_df['G_Score'] = table_df['G_Score'].map('{:.1f}'.format)
        
        table_df = table_df.rename(columns=master_cols)
        print(table_df.to_string(index=False))
        print("=" * 145)


def dispatch_telegram_alerts(final_df):
    # --- TELEGRAM WEBHOOK ALERTS ---
    try:
        from src.infra.telegram_alerts import send_telegram_alert_batch, send_credit_distress_alert_batch
        buy_signals = final_df[final_df['U_Signal'].isin(['STRONG BUY', 'BUY'])].to_dict('records')
        near_expiry = final_df[(final_df['L_Ngay'] < 14) & (final_df['L_Ngay'] > 0)].to_dict('records')
        send_telegram_alert_batch(buy_signals, near_expiry)
        
        # Dispatch credit risk alerts for underlyings in Danger Zone
        distressed_warrants = final_df[final_df['underlying_is_distressed'] == 1]
        if not distressed_warrants.empty:
            unique_underlyings = distressed_warrants['B_MaCPCS'].unique()
            formatted_recs = []
            
            # Retrieve dynamic ML properties calculated during Step 4 mapping
            for ticker in unique_underlyings:
                match_row = distressed_warrants[distressed_warrants['B_MaCPCS'] == ticker].iloc[0]
                
                # Fetch actual live financial metrics from the latest record in final dataset
                # to build high-fidelity natural language commentary for the alert message
                from src.core import config
                distress_file = config.FINAL_DATASET_FILE
                c_ratio = 1.0
                d_ratio = 0.5
                pat_val = 0.0
                ocf_val = 0.0
                icr_val = 9999.0
                if os.path.exists(distress_file):
                    distress_df = pd.read_csv(distress_file)
                    latest_recs = distress_df[distress_df['ticker'] == ticker].sort_values('year')
                    if not latest_recs.empty:
                        last_row = latest_recs.iloc[-1]
                        c_ratio = float(last_row.get('current_ratio', 1.0))
                        d_ratio = float(last_row.get('debt_ratio', 0.5))
                        pat_val = float(last_row.get('profit_after_tax', 0.0))
                        ocf_val = float(last_row.get('operating_cash_flow', 0.0))
                        icr_val = float(last_row.get('ebit_to_interest', 9999.0))
                
                formatted_recs.append({
                    'ticker': ticker,
                    'altman_z_score': float(match_row.get('underlying_altman_z', 0.0)),
                    'xgboost_distress_probability': float(match_row.get('underlying_distress_prob', 0.0)),
                    'current_ratio': c_ratio,
                    'debt_ratio': d_ratio,
                    'profit_after_tax': pat_val,
                    'operating_cash_flow': ocf_val,
                    'ebit_to_interest': icr_val
                })
            send_credit_distress_alert_batch(formatted_recs)
    except Exception as e:
        import sys
        sys.stderr.write(f"\n⚠️ Failed to dispatch Telegram Webhook alerts: {e}\n")


def load_opportunities_from_db(fallback_to_csv: bool = True) -> pd.DataFrame:
    """Load quantitative scan results from SQLite/PostgreSQL Database or fallback to CSV."""
    df = pd.DataFrame()
    try:
        from src.core.database import SessionLocal, MarketOpportunity
        db = SessionLocal()
        try:
            opps = db.query(MarketOpportunity).all()
            if opps:
                data = []
                for o in opps:
                    data.append({
                        "A_MaCW": o.symbol,
                        "B_MaCPCS": o.underlying,
                        "issuer": o.issuer,
                        "C_GiaCW": o.price,
                        "price_change_pct": o.price_change_pct,
                        "intrinsic_value": o.intrinsic_value,
                        "M_GiaHL": o.break_even_price,
                        "Premium_Pct": o.premium_pct,
                        "risk_monthly_pct": o.risk_monthly_pct,
                        "F_DonBay": o.gearing,
                        "L_Ngay": o.days_to_maturity,
                        "G_Score": o.score,
                        "U_Signal": o.decision_signal,
                        "hidden_underlying_price": o.underlying_price,
                        "hidden_ratio": o.ratio,
                        "R_Strike": o.strike_price,
                        "D_Volume": o.volume,
                        "E_GTGD": o.turnover,
                        "S_IV_Pct": (o.implied_volatility_pct * 100) if o.implied_volatility_pct is not None else None,
                        "S_HV_Pct": (o.historical_volatility_pct * 100) if o.historical_volatility_pct is not None else None,
                        "T_Delta": o.delta,
                        "T_Gamma": o.gamma,
                        "T_Theta": o.theta_burn_day,
                        "T_Vega": o.vega,
                        "prob_itm": o.prob_itm,
                        "theo_price": o.theoretical_price,
                        "I_Upside": o.upside_pct,
                        "theo_price_garch": o.garch_theoretical_price,
                        "I_GARCH_Upside": o.garch_upside_pct,
                        "theo_price_merton": o.merton_theoretical_price,
                        "I_Merton_Upside": o.merton_upside_pct,
                        "proj_3d_flat_pct": o.proj_3d_flat_pct,
                        "proj_3d_up_pct": o.proj_3d_up_pct,
                        "proj_3d_down_pct": o.proj_3d_down_pct,
                        "K_ITM_OTM": o.moneyness_category,
                        "underlying_distress_prob": o.underlying_distress_prob,
                        "underlying_is_distressed": o.underlying_is_distressed,
                        "underlying_altman_z": o.underlying_altman_z,
                        "underlying_systemic_prob": o.underlying_systemic_prob,
                        "underlying_systemic_delta": o.underlying_systemic_delta,
                        "underlying_systemic_is_distressed": o.underlying_systemic_is_distressed,
                        "underlying_nim": o.underlying_nim,
                        "underlying_npl": o.underlying_npl,
                        "underlying_casa": o.underlying_casa,
                        "underlying_car": o.underlying_car
                    })
                df = pd.DataFrame(data)
        finally:
            db.close()
    except Exception as e:
        print(f"⚠️ Error loading opportunities from database: {e}")
        
    if df.empty and fallback_to_csv:
        if os.path.exists(REPORT_PATH):
            try:
                df = pd.read_csv(REPORT_PATH)
                print(f"ℹ️ Loaded opportunities from CSV fallback: {REPORT_PATH}")
            except Exception as e:
                print(f"⚠️ Error loading fallback CSV: {e}")
                
    return df

