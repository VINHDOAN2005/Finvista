# -*- coding: utf-8 -*-
"""
📊 NEWS STEP 5: GENERATE COMPREHENSIVE CAR & SENTIMENT REPORT
=============================================================
Outputs professional tables displaying raw returns, market-adjusted CAR,
statistical significance, and AI sentiment-grouped performance breakdowns.
"""

from src.core.utils import logger

def print_impact_report(
    symbol: str, 
    keyword: str, 
    horizon_stats: dict
) -> None:
    """
    Format and print the advanced news impact statistical report.
    """
    if not horizon_stats:
        print("\n❌ Không có đủ dữ liệu thống kê để hiển thị báo cáo.")
        return
        
    print("\n" + "="*112)
    print("🏆  BÁO CÁO THỐNG KÊ TÁC ĐỘNG CỦA TIN TỨC: CUMULATIVE ABNORMAL RETURNS (CAR) & AI SENTIMENT  🏆")
    print("="*112)
    
    # Render filters
    sym_str = symbol.upper() if symbol else "Tất cả các mã"
    key_str = f"'{keyword}'" if keyword else "Không lọc"
    print(f" 🔍 Bộ lọc Mã: {sym_str:<20} | 🔑 Từ khóa tiêu đề: {key_str:<25}")
    print("-"*112)
    
    # Main table header
    header = (
        f"{'Khung (Horizon)':<16} | "
        f"{'Số mẫu':<7} | "
        f"{'P(Vượt Trội)':<13} | "
        f"{'P(Kém Hơn)':<11} | "
        f"{'LN TB tuyệt đối':<15} | "
        f"{'LN Bất thường (CAR)':<20} | "
        f"{'Trị số T':<8} | "
        f"{'Ý nghĩa (p-val)':<15}"
    )
    print(header)
    print("-"*112)
    
    for h, stats in sorted(horizon_stats.items()):
        p_up_car = f"{stats['p_up_car'] * 100:>6.1f}%"
        p_down_car = f"{stats['p_down_car'] * 100:>6.1f}%"
        mean_raw = f"{stats['mean_raw'] * 100:>6.2f}%"
        mean_car = f"{stats['mean_car'] * 100:>6.2f}%"
        t_val = f"{stats['t_stat']:>6.2f}"
        
        # Calculate significance stars
        p = stats["p_value"]
        if p < 0.01:
            sig = f"{p:>6.4f} (***)"
        elif p < 0.05:
            sig = f"{p:>6.4f} (**)"
        elif p < 0.1:
            sig = f"{p:>6.4f} (*)"
        else:
            sig = f"{p:>6.4f} (ns)"
            
        row = (
            f" {h:<14} phiên | "
            f"{stats['count']:>6} | "
            f"{p_up_car:>13} | "
            f"{p_down_car:>11} | "
            f"{mean_raw:>15} | "
            f"{mean_car:>20} | "
            f"{t_val:>8} | "
            f"{sig:<15}"
        )
        print(row)
        
    print("-"*112)
    print(" 💡 Chú thích ý nghĩa thống kê:")
    print("    (***) Rất có ý nghĩa (p < 0.01)    | (**) Có ý nghĩa (p < 0.05)")
    print("    (*)  Ý nghĩa yếu (p < 0.1)        | (ns) Không có ý nghĩa (p >= 0.1)")
    print("    * P(Vượt Trội) = Xác suất Lợi nhuận Bất thường (CAR) > 0% (Hiệu năng tốt hơn thị trường VN30).")
    
    # AI Sentiment analysis breakdown section
    print("\n" + "="*112)
    print("🤖  CHI TIẾT HIỆU NĂNG THEO SẮC THÁI TIN TỨC (AI SENTIMENT ANALYSIS)  🤖")
    print("="*112)
    
    sent_header = (
        f"{'Khung':<8} | "
        f"{'Sắc thái tin':<12} | "
        f"{'Số mẫu':<7} | "
        f"{'LN tuyệt đối TB':<15} | "
        f"{'LN Bất thường TB (CAR)':<22} | "
        f"{'Xác suất Vượt Trội (CAR > 0)':<25}"
    )
    print(sent_header)
    print("-"*112)
    
    for h, stats in sorted(horizon_stats.items()):
        sent_stats = stats.get("sentiment_stats", {})
        if not sent_stats:
            continue
            
        first_row = True
        for sent in ["POSITIVE", "NEGATIVE", "NEUTRAL"]:
            if sent not in sent_stats:
                continue
            s_data = sent_stats[sent]
            
            h_str = f"{h} phiên" if first_row else ""
            sent_str = "Tích cực" if sent == "POSITIVE" else "Tiêu cực" if sent == "NEGATIVE" else "Trung lập"
            
            raw_str = f"{s_data['mean_raw'] * 100:>6.2f}%"
            car_str = f"{s_data['mean_car'] * 100:>6.2f}%"
            p_up_str = f"{s_data['p_up_car'] * 100:>6.1f}%"
            
            row = (
                f"{h_str:<8} | "
                f"{sent_str:<12} | "
                f"{s_data['count']:>6} | "
                f"{raw_str:>15} | "
                f"{car_str:>22} | "
                f"{p_up_str:>25}"
            )
            print(row)
            first_row = False
        print("-"*112)
        
    print("="*112 + "\n")
