# 🚀 HƯỚNG DẪN CHẠY PIPELINE DỰ ĐOÁN KIỆT QUỆ TÀI CHÍNH (QUICK START)

Chào mừng bạn đến với **Hệ thống Thu thập & Dự đoán Kiệt quệ Tài chính Doanh nghiệp Niêm yết (Financial Distress Pipeline)**.
Đây là tài liệu hướng dẫn nhanh cấu trúc mã nguồn và cách vận hành hệ thống.

---

## 📂 1. Cấu Trúc Các Tệp Tin Trong Pipeline

Hệ thống được thiết kế theo dạng Module hóa chia làm 5 bước chính cực kỳ trực quan và chuyên nghiệp:

| Đường dẫn tệp tin | Trách nhiệm & Vai trò trong Pipeline |
| :--- | :--- |
| **`src/common/config.py`** | Quản lý cấu hình hệ thống: Đường dẫn lưu dữ liệu, danh sách sàn (`HOSE`, `HNX`, `UPCOM`), năm thu thập (`2018-2025`), và bộ lọc các ngành tài chính bị loại bỏ. |
| **`src/common/utils.py`** | Chứa các hàm bổ trợ dùng chung: Cấu hình Logger định dạng chuẩn chỉnh (`HH:MM:SS \| LEVEL \| Message`), lưu/mở file JSON/CSV, và Trình quản lý điểm kiểm soát (`CheckpointManager`). |
| **`tools/setup_api.py`** | Tiện ích kiểm tra nhanh môi trường cài đặt và test kết nối API tới `vnstock`. |
| **`src/credit_risk/helpers/inspect_companies.py`** | Phân tích, thống kê tổng quan danh sách toàn bộ các doanh nghiệp niêm yết trên 3 sàn theo cơ cấu ngành. |
| **`src/credit_risk/pipeline/step1_filter_companies.py`** | **[BƯỚC 1]** Đọc danh sách doanh nghiệp niêm yết, loại bỏ các ngân hàng, chứng khoán, bảo hiểm để lọc ra các mã CP phi tài chính mục tiêu. |
| **`src/credit_risk/pipeline/step2_crawl_financials.py`** | **[BƯỚC 2]** Động cơ cào dữ liệu kiên cường. Thực hiện cào BCTC và Giá vốn hóa qua các năm, tự động checkpoint cứu hộ dữ liệu định kỳ và tự áp dụng cơ chế back-off rate-limit. |
| **`src/credit_risk/helpers/filter_raw_data.py`** | Chuyển đổi tệp thô JSON đã cào sang dạng bảng CSV, chuẩn hóa tên chỉ tiêu và kiểm soát/quy đổi đồng bộ đơn vị tiền tệ về đơn vị cơ bản VND. |
| **`src/credit_risk/helpers/inspect_raw_data.py`** | Quét chất lượng dữ liệu thô, thống kê tỷ lệ khuyết thiếu (missing rate) của 6 cột cốt lõi phục vụ phản hồi kỹ thuật. |
| **`src/credit_risk/pipeline/step3_compute_features.py`** | **[BƯỚC 3]** Tính toán hơn 20+ chỉ số tài chính thuộc 4 nhóm (Thanh khoản, Sinh lời, Đòn bẩy, Tăng trưởng) và chỉ số **Altman Z''-Score** cho thị trường mới nổi. |
| **`src/credit_risk/pipeline/step4_label_distress.py`** | **[BƯỚC 4]** Sử dụng hệ thống Luật kinh tế (Rule-based) để tự động gán nhãn rủi ro (`0`: Khỏe mạnh, `1`: Kiệt quệ tài chính) dựa trên lỗ lũy kế, vốn chủ âm, dòng tiền OCF âm liên tiếp. |
| **`src/credit_risk/pipeline/step5_export_dataset.py`** | **[BƯỚC 5]** Gom toàn bộ đặc trưng và nhãn rủi ro, xử lý triệt để NaN và xuất file dữ liệu huấn luyện cuối cùng. |
| **`src/credit_risk/helpers/inspect_indicators.py`** | Quét và in báo cáo thống kê mô tả phân vị (min, max, median, mean) của các tỷ số phái sinh và sự phân bố vùng an toàn theo điểm Z''-Score. |
| **`run_credit_risk.py`** | **[Trình Điều Phối]** Orchestrator chạy tự động liên kết toàn bộ từ Bước 1 đến Bước 5 chỉ với 1 click. |
| **`src/credit_risk/train_model.py`** | Kịch bản Machine Learning. Đọc dữ liệu, chia tập Train/Test theo dòng thời gian chuẩn xác, xử lý mất cân bằng lớp và huấn luyện mô hình **XGBoost Classifier** với độ chính xác cao. |

---

## ⚡ 2. Hướng Dẫn Vận Hành Hệ Thống

Để vận hành toàn bộ hệ thống từ đầu đến khi ra kết quả mô hình, bạn chỉ cần thực hiện theo các bước lệnh đơn giản sau:

### Bước 1: Kiểm tra môi trường và cài đặt thư viện
```powershell
python tools/setup_api.py
```
*Lệnh này sẽ quét xem máy bạn đã cài đủ Pandas, Scikit-learn, XGBoost, vnstock chưa.*

### Bước 2: Chạy kiểm tra phân phối ngành doanh nghiệp (Tùy chọn)
```powershell
python src/credit_risk/helpers/inspect_companies.py
```

### Bước 3: Chạy toàn bộ Pipeline dữ liệu và gán nhãn tự động
Bạn chỉ cần chạy tệp điều phối chính ở thư mục gốc:
```powershell
python run_credit_risk.py
```
Hệ thống sẽ lần lượt chạy liên kết các bước để xuất tệp dữ liệu huấn luyện sạch dạng CSV tại `data/financial_distress/final/financial_distress_dataset.csv`.

### Bước 4: Huấn luyện mô hình Machine Learning dự đoán rủi ro
```powershell
python src/credit_risk/train_model.py
```
*Lệnh này sẽ tiến hành huấn luyện mô hình học máy phân lớp, tối ưu độ chính xác và in ra báo cáo hiệu năng cùng các chỉ số tài chính quan trọng đóng vai trò cảnh báo sớm vỡ nợ doanh nghiệp.*

---
*Tài liệu hướng dẫn kỹ thuật được số hóa tại thư mục dự án Finvista.*

