# 🗺️ Finvista: Real-time Data & Intelligence Roadmap

Bản lộ trình này tập trung vào việc chuyển đổi Finvista từ một hệ thống dựa trên dữ liệu tĩnh/giả lập sang một nền tảng định lượng vận hành hoàn toàn bằng dữ liệu thực thời gian thực (Live Market Intelligence).

## 1. Loại bỏ dữ liệu "Dán cứng" (Hardcoded Cleanup)
**Mục tiêu:** Đảm bảo 100% các chỉ số vĩ mô và trạng thái thị trường được truy vấn từ Database hoặc API thay vì biến hằng số.

*   **Alpha Engine (High Priority):** Thay thế biến `market_regime` trong `src/services/alpha_engine.py` bằng logic tự động nhận diện Regime dựa trên VNINDEX (ví dụ: dùng ADX/RSI/Volatility-based).
*   **Macro Indicators:** Kết nối `macro_indicators.json` trực tiếp vào luồng tính toán của CW Engine thay vì dùng giá trị mặc định 4.5% (Interbank rate).
*   **AI Debate:** Cấu trúc lại prompt của Hội đồng AI để luôn yêu cầu "Price at analysis" là giá `Close` mới nhất vừa được Ingest.

## 2. Luồng dữ liệu Real-time (Live Data Pipeline)
**Mục tiêu:** Tự động hóa quá trình cập nhật dữ liệu nến (OHLCV) mỗi khi chạy mô hình.

*   **Auto-Ingest Hook:** Thêm một bước kiểm tra "Data Recency" (Độ mới của dữ liệu) vào đầu hàm `main` của mỗi mô hình. Nếu dữ liệu cũ hơn 1 giờ, tự động kích hoạt `run.py ingest`.
*   **Websocket Stream:** Tích hợp live stream giá từ SSI/Entrade trực tiếp vào bảng `market_opportunities` để các chỉ số Greeks (Delta, Gamma) biến thiên liên tục trong phiên.
*   **Intraday IV Calculator:** Chuyển từ IV tĩnh (daily) sang IV động (intraday) để bắt kịp các cú biến động mạnh ngay trong phiên.

## 3. Quản lý dữ liệu Giả lập (Simulation & Mocking Strategy)
**Mục tiêu:** Chỉ sử dụng dữ liệu giả lập (Mock) cho mục đích Unit Test và Stress Test, không được phép lọt vào luồng Production.

*   **Strict Mode Flag:** Thêm biến môi trường `FINVISTA_STRICT_DATA=1`. Khi bật, hệ thống sẽ báo lỗi và dừng lại nếu gặp bất kỳ dữ liệu Mock hoặc Fallback nào.
*   **Scenario Generator:** Xây dựng module giả lập các kịch bản cực đoan (Black Swan, Flash Crash) để kiểm thử sức chịu đựng của danh mục (Stress Testing).
*   **Mock Verification:** Tự động gắn tag `is_mock=True` vào bất kỳ dữ liệu giả lập nào trong database để dễ dàng lọc bỏ khi đánh giá hiệu suất thực.

## 4. Kiểm soát chất lượng dữ liệu (Data Quality Gates)
**Mục tiêu:** Đảm bảo mô hình không bao giờ chạy trên dữ liệu rác (Garbage In - Garbage Out).

*   **DQ Gate 2.0:** Mở rộng module `data_quality_report.json` để kiểm tra thêm:
    *   Tính logic giữa Giá CW và Giá Cơ sở (Arbitrage check).
    *   Phát hiện dữ liệu lỗi (Outliers) do API bị lag hoặc sai số.
*   **Drift Detection:** Theo dõi sự thay đổi của phân phối dữ liệu (Data Drift). Nếu đặc tính của thị trường thay đổi quá nhanh so với dữ liệu huấn luyện, hệ thống sẽ tự động gửi cảnh báo yêu cầu Re-train mô hình Credit Risk.

## 5. Hiện đại hóa & Tối ưu hóa cao cấp (Modernization & Optimization)
**Mục tiêu:** Chuyển dịch sang kiến trúc hiệu năng cao và AI minh bạch.

*   **XAI Integration (SHAP):** Nhúng module giải thích mô hình rủi ro tín dụng. Hiển thị các biến số tác động chính lên điểm số Danger Zone của doanh nghiệp.
*   **High-Speed Compute (Numba):** Tối ưu hóa các vòng lặp tính Greeks bằng JIT compiler để hỗ trợ quét kịch bản Stress-test thời gian thực.
*   **OLAP Transformation (DuckDB):** Sử dụng DuckDB để xử lý các tệp Parquet trong Modern Data Stack, thay thế dần các xử lý Pandas nặng nề trên disk.
*   **vnstock v4 Support:** Hoàn tất việc chuyển đổi toàn bộ pipeline sang cấu trúc Domain-based của vnstock 4.0.4.

---
**Trạng thái hiện tại:**
- [x] Refactor 7-Layer AI Architecture.
- [x] Unified CLI entry point (`run.py`).
- [x] Initial Credit Risk Pipeline (Steps 1-8).
- [x] vnstock 4.0 Migration (Macro & Credit Crawlers).
- [ ] XAI / SHAP Dashboard (Next Step).
- [ ] Numba Optimization for Greeks (Next Step).
- [ ] Real-time Websocket Integration (Next Step).
