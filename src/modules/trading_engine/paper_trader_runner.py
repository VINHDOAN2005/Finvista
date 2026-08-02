# -*- coding: utf-8 -*-
"""
🏆 FINVISTA: HOSE-COMPLIANT QUANTITATIVE PAPER TRADING PORTFOLIO LAUNCHER
========================================================================
Usage:
  python run_paper_trader.py --portfolio    # View demo account dashboard
  python run_paper_trader.py --scan         # Scan signals and execute trades
  python run_paper_trader.py --scan --force # Scan and execute (bypass hours check)
  python run_paper_trader.py --reset        # Reset demo account cash

Author: samvo
"""
import sys
import os
import argparse

# Ensure project root is on PYTHONPATH when running as a script (python src/trading/paper_trader_runner.py)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.modules.trading_engine.paper_trader import scan_and_trade, print_portfolio_dashboard, reset_portfolio

# Force stdout encoding to UTF-8 to handle Vietnamese text beautifully on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def main():
    parser = argparse.ArgumentParser(description="Finvista HOSE-Compliant Paper Trading & Live Validation System")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--portfolio', '-p', action='store_true', help="Print live quantitative trading dashboard")
    group.add_argument('--scan', '-s', action='store_true', help="Scan latest BSM signals and execute orders")
    group.add_argument('--reset', '-r', action='store_true', help="Reset DEMO account cash to 100,000,000 VND")
    
    parser.add_argument('--force', '-f', action='store_true', help="Bypass HOSE market hours checks (simulate after hours)")
    parser.add_argument('--loop', '-l', type=int, help="Run in continuous loop scanning and refreshing live market data every N seconds (e.g. 300 for 5 mins)")
    args = parser.parse_args()
    
    if args.reset:
        reset_portfolio()
        print("✅ Demo paper trading account cash successfully reset to 100,000,000đ.")
        print_portfolio_dashboard()
        return
        
    if args.portfolio:
        print_portfolio_dashboard()
        return
        
    if args.scan:
        if args.loop:
            import time
            from datetime import datetime
            from src.modules.cw_pricing.backtest.run_analysis import main as refresh_analysis
            
            print(f"🔄 Khởi chạy VÒNG LẶP GIAO DỊCH TỰ ĐỘNG LIÊN TỤC mỗi {args.loop} giây...")
            print("💡 Hệ thống sẽ tự động:")
            print("   1. Cào giá trực tuyến thời gian thực (VCI Live API) & tính toán BSM/Greeks.")
            print("   2. Kiểm soát rủi ro (Cắt lỗ -15%, Chốt lời +20%, Theta Decay cảnh báo đáo hạn).")
            print("   3. Khớp lệnh mua tự động HOSE-compliant (Vốn tối đa 20%/mã, lô tối thiểu 100 CW).")
            print("=" * 125)
            
            # Keep backup of original sys.argv
            orig_argv = sys.argv
            
            try:
                while True:
                    dt_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    print(f"\n[🔔 VÒNG LẶP HỆ THỐNG - {dt_str}] Bắt đầu làm mới dữ liệu & Greeks...")
                    
                    try:
                        # Run the quantitative pipeline in silent mode to keep terminal output clean and focused
                        sys.argv = ['run_cw.py', '--silent']
                        refresh_analysis()
                    except Exception as e:
                        print(f"⚠️ Cảnh báo: Lỗi nạp dữ liệu live từ VCI API: {e}. Vẫn quét lệnh với cache hiện tại.")
                    
                    print("🏁 Tiến hành quét kiểm tra và kích hoạt lệnh...")
                    actions = scan_and_trade(force=args.force)
                    print("📝 Nhật ký khớp lệnh:")
                    for act in actions:
                        print(f"  * {act}")
                    
                    print("\n📊 BẢNG ĐIỀU KHIỂN TÀI KHOẢN CẬP NHẬT:")
                    print_portfolio_dashboard()
                    
                    print(f"💤 Đang nghỉ {args.loop} giây... Nhấn Ctrl+C để dừng tự động hóa.")
                    time.sleep(args.loop)
            except KeyboardInterrupt:
                print("\n🛑 Đã nhận tín hiệu dừng! Vòng lặp giao dịch tự động kết thúc an toàn.")
                # Restore original sys.argv
                sys.argv = orig_argv
                return
        else:
            print("🏁 Running automated Volatility Arbitrage Strategy & Risk Management scans...")
            actions = scan_and_trade(force=args.force)
            print("\n📝 Execution logs:")
            for act in actions:
                print(f"  * {act}")
            print("\n📊 Updating portfolio dashboard...")
            print_portfolio_dashboard()

if __name__ == "__main__":
    main()
