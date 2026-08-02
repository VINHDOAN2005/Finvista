# 🚀 HƯỚNG DẪN KHỞI CHẠY NHANH FINVISTA (QUICK START)

Chào mừng bạn đến với **Hệ thống Định giá, Giao dịch Giả lập & Cảnh báo Sớm Chứng quyền Finvista (Finvista SaaS Engine)**.
Tài liệu này hướng dẫn chi tiết cách thiết lập môi trường, cấu hình biến bảo mật và vận hành hệ thống một cách nhanh nhất qua trình CLI điều khiển trung tâm `run.py`.

---

## 📂 1. Cấu Trúc File & Vai Trò Lõi Hệ Thống

Dự án được tổ chức theo chuẩn **Clean Architecture** (Kiến trúc Sạch) giúp cô lập logic nghiệp vụ toán học, cơ sở dữ liệu và API giao tiếp:

| Đường dẫn tệp tin | Vai trò & Trách nhiệm trong Hệ Thống |
| :--- | :--- |
| **[run.py](run.py)** | **[Entrypoint Duy Nhất]** CLI điều khiển trung tâm. Tích hợp banner ASCII, menu điều hướng tiếng Việt để gọi tất cả các tính năng. |
| **[src/api/main.py](src/api/main.py)** | **[API Gateway]** Khởi chạy server FastAPI. Tích hợp Rate Limiting (`slowapi`), WebSockets thời gian thực, xác thực JWT và CORS. |
| **[src/common/database.py](src/common/database.py)** | **[ORM Persistence]** Quản trị cơ sở dữ liệu SQLite (`finvista.db`) bằng SQLAlchemy. Lưu trữ tài khoản, số dư NAV, vị thế và lịch sử giao dịch. |
| **[src/common/telegram_alerts.py](src/common/telegram_alerts.py)** | **[Webhook Alerts]** Động cơ đẩy thông báo HTML tự động về cơ hội `STRONG BUY` hoặc cảnh báo Theta đáo hạn (<14 ngày) qua Telegram. |
| **[src/quant/pricing_core.py](src/quant/pricing_core.py)** | **[Math Engine]** Công thức Black-Scholes-Merton, tính các Greeks lý thuyết ($\Delta, \Gamma, \Theta, \nu$) và trình giải ngược Newton-Raphson IV. |
| **[src/etl/credit_pipeline.py](src/etl/credit_pipeline.py)** | **[Steps 1–5]** Pipeline thu thập, làm sạch, tính chỉ số và gán nhãn rủi ro kiệt quệ tài chính cho ~1,533 doanh nghiệp niêm yết. |
| **[src/models/credit_step6_train_model.py](src/models/credit_step6_train_model.py)** | **[Step 6 · ML Train]** Chia Train/Test theo dòng thời gian, huấn luyện & so sánh 11+ mô hình, xuất `best_distress_model.pkl`. |
| **[src/models/credit_step7_evaluate_market.py](src/models/credit_step7_evaluate_market.py)** | **[Step 7 · Inference]** Chạy batch inference XGBoost toàn thị trường, xuất `market_health_report.csv` phân loại GREEN / YELLOW / RED. |
| **[src/models/credit_step8_contagion_model.py](src/models/credit_step8_contagion_model.py)** | **[Step 8 · DebtRank]** Thuật toán lan truyền rủi ro hệ thống (DebtRank) trên đồ thị mạng lưới 1,533 doanh nghiệp, xuất `systemic_health_report.csv`. |
| **[src/models/network_builder.py](src/models/network_builder.py)** | **[Network Layer]** Xây dựng đồ thị có hướng NetworkX (Conglomerate + Industry + Price Correlation edges) phục vụ Step 8. |
| **[tests/](tests/)** | **[Test Suite]** 15/15 bài test tự động cho REST endpoints và lõi toán học Greeks (chạy qua `pytest`). |
| **[alembic/](alembic/)** | **[Migrations]** Tự động đồng bộ hóa cấu trúc Database schema mà không làm mất mát dữ liệu. |

---

## ⚙️ 2. Thiết Lập Môi Trường Lần Đầu

### Bước 1: Sao chép tệp cấu hình và kích hoạt bảo mật
Nhân bản file cấu hình mẫu `.env.example` thành tệp nội bộ `.env` để nạp các thông tin nhạy cảm:
```powershell
copy .env.example .env
```
Mở tệp `.env` vừa tạo và điền các khóa bí mật của bạn (ví dụ: `JWT_SECRET_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` để nhận tin nhắn cảnh báo).

### Bước 2: Cài đặt thư viện phụ thuộc
Hệ thống sử dụng các thư viện Python gọn nhẹ nhưng mạnh mẽ. Tiến hành cài đặt qua:
```powershell
pip install -r requirements.txt
```

### Bước 3: Đồng bộ cơ sở dữ liệu ban đầu (Database Migration)
Sử dụng Alembic để tự động tạo cấu trúc bảng dữ liệu sạch:
```powershell
alembic upgrade head
```

---

## ⚡ 3. Hướng Dẫn Vận Hành Dự Án Qua CLI `run.py`

Mở terminal tại thư mục gốc và sử dụng các câu lệnh hợp nhất sau:

### Chức năng A: Khởi chạy API Gateway phục vụ Frontend
Khởi chạy API server cổng 8008 tích hợp đầy đủ WebSockets và Rate Limiting:
```powershell
python run.py api
```
*   *Tài liệu tương tác Swagger:* Truy cập đường dẫn [http://127.0.0.1:8008/docs](http://127.0.0.1:8008/docs).

### Chức năng B: Định giá chứng quyền thời gian thực & Cảnh báo Telegram
Quét toàn bộ thị trường CW, tính IV thực tế, Greeks lý thuyết và lọc cơ hội đầu tư:
```powershell
# Chạy quét thị trường theo chiến thuật Balanced
python run.py cw --strategy balanced
# hoặc alias tương đương:
python run.py scan --strategy balanced

# Gom nhóm theo Cổ phiếu cơ sở và xuất báo cáo CSV ra data/
python scripts/run_cw.py --strategy balanced --all
```

### Chức năng C: Phân tích chênh lệch biến động IV vs HV lịch sử
Giải ngược IV lịch sử 10 ngày gần nhất và so sánh với biến động thực tế HV của cổ phiếu cơ sở:
```powershell
python run.py history --symbol CACB2510 --days 10
```

### Chức năng D: Bot giao dịch giả lập tự động (Paper Trading)
Quản trị vị thế, kiểm soát chốt lời cắt lỗ HOSE thời gian thực:
```powershell
# Quét danh mục và tự động thực thi tín hiệu chốt lời (+20%), cắt lỗ (-15%)
python run.py trade --scan

# Xem tài sản ròng NAV, số dư tiền mặt và vị thế mở của bạn
python run.py trade --portfolio
```

### Chức năng E: Pipeline Kiệt quệ Tài chính — 8 bước hoàn chỉnh

Pipeline được chia thành **8 bước liên tiếp** theo luồng dữ liệu một chiều:

| Bước | Lệnh CLI | Mô tả |
| :--: | :--- | :--- |
| **1–5** | `python run.py credit` | Thu thập BCTC, làm sạch, tính chỉ số, gán nhãn Altman Z'' |
| **6** | `python run.py credit --train` | Huấn luyện & xuất mô hình XGBoost tốt nhất (`best_distress_model.pkl`) |
| **7** | `python run.py credit --evaluate` | Chạy batch inference toàn thị trường → `market_health_report.csv` |
| **8** | `python run.py credit --contagion` | Mô phỏng lan truyền DebtRank → `systemic_health_report.csv` (Hard-Gate CW) |

```powershell
# Bước 1–5: Chạy pipeline ETL thu thập BCTC và gán nhãn Altman Z''
python run.py credit

# Bước 6: Huấn luyện mô hình học máy XGBoost dự báo Danger Zone
python run.py credit --train
```

---
*Tài liệu vận hành nhanh được số hóa và chuẩn hóa tại UPGen Deutsches Haus Tower.*
