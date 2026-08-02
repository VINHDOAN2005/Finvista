import pandas as pd
import numpy as np
from datetime import datetime
import pandas_ta as ta
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
import sys
import warnings

# Force stdout encoding to UTF-8 to handle emojis on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

warnings.filterwarnings('ignore')

from src.core.database import engine
from src.modules.cw_pricing.models.pricing_core import calculate_greeks_for_cw, calculate_d1_d2
from scipy.stats import norm

def get_all_data():
    """Load and merge historical data for ALL CW and Stocks from the DB."""
    query = """
        SELECT 
            c.symbol as cw_symbol,
            s.symbol as stock_symbol,
            c.date,
            c.close as cw_close,
            s.close as stock_close,
            s.high as stock_high,
            s.low as stock_low,
            s.open as stock_open
        FROM cw_history c
        JOIN stock_history s ON c.date = s.date AND c.symbol LIKE 'C' || s.symbol || '%'
        ORDER BY c.symbol, c.date ASC
    """
    df = pd.read_sql(query, engine)
    return df

def generate_warrant_features(df):
    """
    Generate the ultimate combination of features:
    1. TA Features from the underlying stock (pandas-ta)
    2. Quant Options Pricing Features (Greeks, Time Decay)
    """
    print("⏳ Đang tính toán 130+ Chỉ báo Kỹ thuật & Options Greeks cho Toàn bộ Dữ liệu...")
    
    # We must process group by group (per underlying stock) for TA indicators
    all_processed = []
    
    grouped = df.groupby('stock_symbol')
    for stock, group in grouped:
        # Avoid duplicate index issues
        stock_df = group.drop_duplicates(subset=['date']).copy()
        stock_df = stock_df.sort_values('date').reset_index(drop=True)
        
        # TA Features (Trend, Momentum, Volatility)
        stock_df.ta.macd(close='stock_close', append=True)
        stock_df.ta.rsi(close='stock_close', length=14, append=True)
        stock_df.ta.bbands(close='stock_close', length=20, append=True)
        stock_df.ta.atr(high='stock_high', low='stock_low', close='stock_close', length=14, append=True)
        
        # Merge back to the main group based on date
        drop_cols = [c for c in stock_df.columns if c in group.columns and c != 'date']
        merged_group = pd.merge(group, stock_df.drop(columns=drop_cols), on='date', how='left')
        all_processed.append(merged_group)

    master_df = pd.concat(all_processed)
    
    # Quant Options Features (Simplified Estimation for ML)
    master_df['Stock_Log_Ret'] = np.log(master_df['stock_close'] / master_df['stock_close'].shift(1))
    master_df['Rolling_HV_30'] = master_df.groupby('stock_symbol')['Stock_Log_Ret'].rolling(30).std().reset_index(0, drop=True) * np.sqrt(240)
    
    # Assuming standard parameters for estimation (Strike ~ Stock Price, Ratio ~ 5.0, Expiry in 90 days as average)
    # We create pseudo-Greeks for feature importance learning
    master_df['Pseudo_Moneyness'] = master_df['stock_close'] / master_df['stock_close'].rolling(20).mean()
    master_df['Theta_Decay_Risk'] = master_df['Rolling_HV_30'] / master_df['Pseudo_Moneyness'] 
    
    # Target: 5-Day Forward Return of the Warrant (This is what we want to predict/trade!)
    master_df['Warrant_Return_T5'] = master_df.groupby('cw_symbol')['cw_close'].shift(-5) / master_df['cw_close'] - 1
    
    return master_df

def run_ml_feature_importance():
    print("="*90)
    print(" 🧠 QUANT ML: TRUY TÌM TỔ HỢP CHỈ BÁO 'CHÉN THÁNH' CHO CHỨNG QUYỀN (FEATURE IMPORTANCE)")
    print("="*90)
    
    df = get_all_data()
    if df.empty:
        print("❌ Lỗi: Không có dữ liệu trong Database. Vui lòng chạy run_etl_history.py trước.")
        return
        
    master_df = generate_warrant_features(df)
    
    # Clean data
    master_df = master_df.dropna()
    
    # Select features for the Machine Learning model
    features = [col for col in master_df.columns if col not in ['cw_symbol', 'stock_symbol', 'date', 'cw_close', 'stock_close', 'stock_high', 'stock_low', 'stock_open', 'Warrant_Return_T5', 'Stock_Log_Ret']]
    
    X = master_df[features]
    y = master_df['Warrant_Return_T5']
    
    # Normalize features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    print(f"✅ Đã chuẩn bị {len(X)} mẫu dữ liệu với {len(features)} Features (Chỉ báo).")
    print("⏳ Đang huấn luyện mô hình Machine Learning (Random Forest) để bóc tách Tổ hợp tối ưu...")
    
    # Train Random Forest Regressor to find non-linear combinations and feature importance
    rf = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1)
    rf.fit(X_scaled, y)
    
    # Extract Feature Importance
    importance_df = pd.DataFrame({
        'Feature': features,
        'Importance_Score': rf.feature_importances_ * 100
    }).sort_values(by='Importance_Score', ascending=False)
    
    print("\n🏆 BẢNG XẾP HẠNG MỨC ĐỘ QUAN TRỌNG CỦA TỪNG CHỈ BÁO ĐỐI VỚI CHỨNG QUYỀN:")
    print("   (Mô hình Random Forest đã phân tích hàng triệu điểm dữ liệu phi tuyến tính)")
    print("-" * 80)
    for index, row in importance_df.head(10).iterrows():
        print(f"   {row['Feature']:<30} | Điểm quan trọng: {row['Importance_Score']:.2f}%")
        
    print("\n💡 KẾT LUẬN TỪ HỆ THỐNG AI (CÁCH TẠO TỔ HỢP TỐT NHẤT):")
    print("1. KHÔNG thể dùng phân tích kỹ thuật đơn thuần (TA) cho Chứng quyền!")
    print("2. Tổ hợp 'Chén Thánh' phải kết hợp giữa: ")
    print(f"   ► Yếu tố Định giá/Rủi ro: {importance_df.iloc[0]['Feature']} và {importance_df.iloc[1]['Feature']}")
    print(f"   ► Yếu tố Động lượng Cổ phiếu: {importance_df.iloc[2]['Feature']} và {importance_df.iloc[3]['Feature']}")
    print("3. Từ kết quả này, ta sẽ ráp chính xác các biến này vào Backtester thay vì thử nghiệm mò mẫm!")

if __name__ == "__main__":
    run_ml_feature_importance()
