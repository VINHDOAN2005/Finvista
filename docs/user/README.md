# 📂 Thư Mục Tài Liệu Finvista (Finvista Docs Workspace)

Mục lục các tài liệu và tài nguyên kỹ thuật trong thư mục `docs/`. Toàn bộ tài liệu dự án đã được quy hoạch, phân loại và gộp về các thư mục chức năng để dễ dàng theo dõi và phát triển:

---

## 📋 Phân Loại Thư Mục Tài Liệu

### 🏁 1. Hướng Dẫn Sử Dụng (Guides)
*   **[quick_start.md](guides/quick_start.md)**: Hướng dẫn khởi chạy nhanh dự án, cấu hình môi trường và vận hành các tập lệnh chính.

### 🛠️ 2. Kỹ Thuật & Nghiên Cứu (Tech)
*   **[saas_architecture_blueprint.md](tech/saas_architecture_blueprint.md)**: Bản thiết kế kiến trúc SaaS chi tiết (Web/Mobile/API Gateway) và lộ trình hạ tầng kỹ thuật.
*   **[modern_data_stack_architecture.md](tech/modern_data_stack_architecture.md)**: Tài liệu thiết kế Modern Data Stack (Airflow, MinIO, DuckDB, Iceberg, Trino, Superset) và cơ chế Data Quality Gates để scale hệ thống lên Big Data.
*   **[golden_modern_architecture.md](tech/golden_modern_architecture.md)**: Định hướng kiến trúc ứng dụng bền vững (Clean Architecture) cho các module của Finvista.
*   **[telegram_webhook_setup.md](tech/telegram_webhook_setup.md)**: Quy trình cấu hình và cài đặt Webhook phục vụ gửi cảnh báo rủi ro/giao dịch qua Telegram.
*   **[cw_metrics_handbook.md](tech/cw_metrics_handbook.md)**: Cẩm nang giải thích dễ hiểu các chỉ số chứng quyền (Delta, Theta, Gearing, IV...) cho người mới bắt đầu.
*   **[credit_distress_audit.md](tech/credit_distress_audit.md)**: Báo cáo kiểm định chất lượng mô hình phân loại nợ xấu và kiệt quệ doanh nghiệp cơ sở.
*   **[modern_market_research.md](tech/modern_market_research.md)**: Nghiên cứu định lượng nâng cao bao gồm Merton Structural Model, GEX (Gamma Exposure), Leland Volatility, CBBC & Put Warrants.
*   **[modern_data_requirements.md](tech/modern_data_requirements.md)**: Bảng ma trận tương quan, tác động dữ liệu và các cổng API thu thập biến số mới (Total Debt, L2 Bid-Ask Spread).
*   **[decision_making_pipeline.md](tech/decision_making_pipeline.md)**: Thiết kế luồng pipeline ra quyết định kết hợp cả các tín hiệu kỹ thuật phái sinh và sức khỏe tài chính doanh nghiệp.
*   **[rccr_conformal_risk_framework.md](tech/rccr_conformal_risk_framework.md)**: Khung phân tích kiểm soát rủi ro Conformal (RCCR) nhằm chặn đứng tổn thất cực đoan trong giao dịch chứng quyền.

### 🗺️ 3. Kế Hoạch & Lộ Trình (Planning)
*   **[unified_integration_plan.md](planning/unified_integration_plan.md)**: Kế hoạch hợp nhất công cụ định giá Chứng quyền (CW) và mô hình Dự đoán Kiệt quệ Tài chính.
*   **[financial_distress_roadmap.md](planning/financial_distress_roadmap.md)**: Sơ đồ kiến trúc 5 tầng của hệ thống dự đoán kiệt quệ tài chính của 1,447 doanh nghiệp.
*   **[roadmap.md](planning/roadmap.md)**: Lộ trình và các bước phát triển tính năng chi tiết của dự án Finvista.
*   **[roadmap_realtime.md](planning/roadmap_realtime.md)**: Kế hoạch tích hợp dữ liệu Real-time Websocket, xử lý Intraday IV, và dynamic risk-free rate.
*   **[readme_updates.md](planning/readme_updates.md)**: Nhật ký ghi nhận các thay đổi, sửa lỗi và nâng cấp quan trọng của dự án.

### 📚 4. Tài Liệu Tham Khảo (Ref)
*   **[ref/](ref/)**: Bộ tài liệu 28 chương nghiên cứu chuyên sâu về Quản trị rủi ro & Định giá phái sinh của tác giả John C. Hull.
