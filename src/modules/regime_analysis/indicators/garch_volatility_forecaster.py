# -*- coding: utf-8 -*-
"""
🏆 FINVISTA: GARCH(1,1) VOLATILITY FORECASTER & OPTIONS CALIBRATOR
================================================================
Fits a GARCH(1,1) model with Student's t distribution on historical daily returns 
of underlying stocks. Compares GARCH conditional volatility against standard 
historical rolling volatility to prove GARCH's ability to capture volatility clustering.

Author: samvo
"""
import os
import sys
import pandas as pd
import numpy as np
import warnings
from arch import arch_model
from src.core.database import engine

# Force terminal UTF-8 encoding on Windows to ensure flawless Vietnamese text rendering
if sys.platform == 'win32':
    import io
    if sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    if sys.stderr.encoding.lower() != 'utf-8':
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

warnings.filterwarnings('ignore')

def get_underlying_symbols():
    """Fetch unique underlying stock symbols from database."""
    query = "SELECT DISTINCT symbol FROM stock_history"
    df = pd.read_sql(query, engine)
    return df['symbol'].tolist()

def fetch_stock_returns(symbol):
    """Fetch historical stock price and calculate daily log returns."""
    query = f"""
        SELECT date, close 
        FROM stock_history 
        WHERE symbol = '{symbol}' 
        ORDER BY date ASC
    """
    df = pd.read_sql(query, engine)
    if df.empty or len(df) < 50:
        return None
    
    df['date'] = pd.to_datetime(df['date'])
    df['close'] = df['close'].astype(float)
    df['log_return'] = np.log(df['close'] / df['close'].shift(1))
    return df.dropna().reset_index(drop=True)

def fit_garch_model(df_returns, symbol):
    """Fits GARCH(1,1) with Student's t-distribution on returns."""
    # Scale returns by 100 for better optimization stability
    returns = df_returns['log_return'] * 100.0
    
    # Define GARCH(1,1) model with Student's t distribution (to handle fat tails)
    model = arch_model(returns, mean='Constant', vol='GARCH', p=1, q=1, dist='studentst')
    
    try:
        res = model.fit(disp='off')
        
        # Get parameter estimates
        omega = res.params['omega']
        alpha = res.params['alpha[1]']
        beta = res.params['beta[1]']
        nu = res.params['nu'] # Degrees of freedom
        
        # Check stability condition: alpha + beta < 1
        persistence = alpha + beta
        is_stable = persistence < 1.0
        
        # Forecast 1-day ahead conditional variance
        forecast = res.forecast(horizon=1)
        next_day_variance = forecast.variance.iloc[-1, 0] # Scale is still returns * 100
        
        # Convert next-day standard deviation to annualized volatility
        # Standard deviation of scaled returns is sqrt(variance). 
        # Since returns were scaled by 100, we divide the std by 100 to unscale, then annualize with sqrt(240).
        garch_vol_ann = (np.sqrt(next_day_variance) / 100.0) * np.sqrt(240) * 100.0
        
        # Calculate standard historical 30-day volatility for comparison
        hist_30d_vol_ann = df_returns['log_return'].tail(30).std() * np.sqrt(240) * 100.0
        
        # Current daily return
        latest_return = df_returns['log_return'].iloc[-1] * 100.0
        
        return {
            'symbol': symbol,
            'omega': omega,
            'alpha': alpha,
            'beta': beta,
            'persistence': persistence,
            'degrees_of_freedom_nu': nu,
            'is_stable': is_stable,
            'garch_forecast_vol_pct': garch_vol_ann,
            'hist_30d_vol_pct': hist_30d_vol_ann,
            'deviation_pct': garch_vol_ann - hist_30d_vol_ann,
            'latest_return_pct': latest_return
        }
    except Exception as e:
        print(f"⚠️ Failed to fit GARCH(1,1) for {symbol}: {e}")
        return None

def main():
    print("=" * 95)
    print(" 📉 KHỞI CHẠY HỆ THỐNG DỰ BÁO BIẾN ĐỘNG ĐIỀU KIỆN GARCH(1,1) & ĐÁNH GIÁ ĐÁM MÂY BIẾN ĐỘNG")
    print("=" * 95)
    
    symbols = get_underlying_symbols()
    if not symbols:
        print("❌ Error: No underlying stock symbols found in database.")
        sys.exit(1)
        
    print(f"📊 Tìm thấy {len(symbols)} cổ phiếu cơ sở trong CSDL. Bắt đầu xử lý dữ liệu...")
    
    results = []
    for sym in symbols:
        df_ret = fetch_stock_returns(sym)
        if df_ret is not None:
            metrics = fit_garch_model(df_ret, sym)
            if metrics:
                results.append(metrics)
                
    if not results:
        print("❌ Error: No GARCH models converged successfully.")
        sys.exit(1)
        
    results_df = pd.DataFrame(results).sort_values('deviation_pct', key=abs, ascending=False)
    
    # Display comparison table
    print("\n" + "=" * 115)
    print(f"{'Cổ Phiếu':<10} | {'GARCH Vol (T+1)':>15} | {'Hist 30d Vol':>15} | {'Chênh Lệch':>12} | {'Hệ Số ARCH (α)':>15} | {'Hệ Số GARCH (β)':>15} | {'Tính Bền Vững':>15}")
    print("-" * 115)
    
    for _, r in results_df.iterrows():
        stable_status = "BỀN VỮNG" if r['is_stable'] else "PHÁT TÁN ⚠️"
        print(f"{r['symbol']:<10} | {r['garch_forecast_vol_pct']:13.2f}% | {r['hist_30d_vol_pct']:13.2f}% | {r['deviation_pct']:+11.2f}% | {r['alpha']:15.4f} | {r['beta']:15.4f} | {stable_status:<15}")
    print("=" * 115)
    
    # Save parameters to processed files
    output_dir = "data/processed"
    os.makedirs(output_dir, exist_ok=True)
    csv_path = os.path.join(output_dir, "garch_vol_report.csv")
    results_df.to_csv(csv_path, index=False, encoding='utf-8')
    
    print(f"\n💾 Đã lưu báo cáo so sánh biến động GARCH vào: {csv_path}")
    print("\n💡 PHÂN TÍCH CHUYÊN SÂU TỪ HỆ THỐNG QUAN T:")
    print("1. Hiện tượng Đám mây biến động (Volatility Clustering):")
    print("   - Khi chênh lệch (GARCH Vol - Hist 30d) mang giá trị DƯƠNG (+): Cổ phiếu đang gặp cú sốc biến động mạnh gần đây.")
    print("     GARCH lập tức tăng dự báo độ biến động ngày mai lên cao, giúp giá lý thuyết chứng quyền phản ánh đúng rủi ro.")
    print("   - Khi chênh lệch mang giá trị ÂM (-): Cổ phiếu đang rơi vào pha bình yên kéo dài.")
    print("     GARCH hạ giá trị dự báo thấp hơn trung bình lịch sử, tránh định giá đắt vô lý cho Option.")
    print("2. Ứng dụng thực tế:")
    print("   - Thay thế việc dùng Flat Volatility trong mô hình Black-Scholes để định giá chính xác chênh lệch Implied Volatility (IV).")

if __name__ == "__main__":
    main()
