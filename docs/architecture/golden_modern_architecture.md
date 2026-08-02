# 🏛️ CẤU TRÚC "GOLDEN MODERN" - FINVISTA ARCHITECTURE v2.0

Để hiện thực hóa một hệ thống AI Quant Agent quy mô Enterprise, Finvista tuân thủ cấu trúc **Golden Modern Architecture**. Đây là sự kết hợp giữa **Clean Architecture**, **Domain-Driven Design (DDD)** và **Modern Pythonic Best Practices**.

---

## 📂 1. Cấu Trúc Thư Mục Chuẩn (Project Layout)

```text
finvista/
├── .env                  # Cấu hình môi trường (Secrets, API Keys)
├── .gitignore            # Loại trừ các file không cần thiết cho Git
├── alembic.ini           # Cấu hình Database Migration
├── main.py               # Điểm khởi đầu ứng dụng (FastAPI entrypoint)
├── requirements.txt      # Danh sách thư viện phụ thuộc
├── run.py                # Unified CLI Manager (Scan, Train, Alert)
│
├── alembic/              # Quản lý lịch sử thay đổi Database
│
├── data/                 # Lưu trữ dữ liệu (Bị .gitignore ngoại trừ các file mẫu)
│   ├── raw/              # Dữ liệu thô từ SSI/Vnstock
│   ├── processed/        # Dữ liệu đã làm sạch & Feature Engineering
│   ├── final/            # Dataset cuối cùng cho ML
│   └── finvista.db       # Database SQLite (SaaS Core)
│
├── docs/                 # Tài liệu kỹ thuật & Roadmap
│
├── logs/                 # Nhật ký vận hành hệ thống
│
├── models/               # Lưu trữ các file mô hình đã huấn luyện (.pkl, .onnx)
│
├── src/                  # MÃ NGUỒN CHÍNH (Core Logic)
│   ├── api/              # LỚP GIAO TIẾP (Delivery Layer)
│   │   ├── routes/       # Các Endpoint FastAPI (Warrants, Credit, Chat)
│   │   ├── dependencies.py # Quản lý DI, Auth, Limiter
│   │   ├── websocket.py  # Xử lý Real-time Streaming
│   │   └── main.py       # Khởi tạo FastAPI App
│   │
│   ├── common/           # LỚP TIỆN ÍCH (Shared Infrastructure)
│   │   ├── ai_client.py  # Unified Gemini/OpenAI Client
│   │   ├── config.py     # Quản lý hằng số & Đường dẫn
│   │   ├── database.py   # SQLAlchemy Models & Session
│   │   └── utils.py      # Các hàm helper dùng chung
│   │
│   ├── etl/              # LỚP TRÍCH XUẤT (Data Ingestion)
│   │   ├── extractors/   # Cào dữ liệu từ SSI, Vnstock, Vietcap
│   │   └── loaders/      # Đẩy dữ liệu vào DB/CSV
│   │
│   ├── quant/            # LỚP ĐỊNH LƯỢNG (Quantitative Core - Domain)
│   │   ├── pricing/      # Black-Scholes, GARCH, Greeks calculation
│   │   ├── indicators/   # Technical Indicators (PatchTST logic)
│   │   └── engines/      # Scanner & Ranking logic
│   │
│   ├── models/           # LỚP HỌC MÁY (ML/Deep Learning)
│   │   ├── credit/       # XGBoost, Altman Z-Score, OCF Forensics
│   │   └── systemic/     # DebtRank & Network Analysis
│   │
│   ├── services/         # LỚP NGHIỆP VỤ (Application Business Logic)
│   │   ├── warrant_service.py
│   │   ├── credit_service.py
│   │   └── ai_committee_service.py # Orchestrator cho 7-Layer AI
│   │
│   └── trading/          # LỚP GIAO DỊCH (Execution Layer)
│       ├── paper_trader.py
│       └── telegram_alerts.py
│
└── tests/                # Kiểm thử tự động (Unit, Integration, E2E)
```

---

## 🛠️ 2. Các Nguyên Tắc "Golden" Cốt Lõi

### A. Separation of Concerns (Phân tách Trách nhiệm)
*   **API Layer:** Không chứa logic tính toán. Chỉ nhận Request, gọi Service và trả về Response.
*   **Service Layer:** Nơi điều phối (Orchestration). Service gọi Quant Engine để lấy số, gọi DB để lưu, gọi AI Client để phân tích.
*   **Quant/Model Layer:** Trái tim của hệ thống. Chỉ chứa toán học và logic định lượng thuần túy, không phụ thuộc vào Web hay DB.

### B. Dependency Injection (Tiêm phụ thuộc)
*   Sử dụng Singleton cho `AIClient` và `Database Session`.
*   Truyền các instance vào class thông qua constructor để dễ dàng Mocking khi viết Tests.

### C. Asynchronous First (Ưu tiên Bất đồng bộ)
*   Tất cả các lệnh gọi IO (API bên ngoài, Database, AI) đều sử dụng `async/await`.
*   Sử dụng `asyncio.gather` để chạy song song các Agent trong hội đồng AI nhằm tối ưu thời gian phản hồi.

### D. Data Integrity & Schema
*   Sử dụng **Pydantic** để validate dữ liệu đầu vào/đầu ra API.
*   Sử dụng **SQLAlchemy** làm ORM để đảm bảo tính nhất quán của dữ liệu.
*   Sử dụng **Alembic** để quản lý version của Database (không bao giờ sửa DB thủ công).

### E. AI Safety & Determinism (HITL)
*   **Strict JSON Output:** AI luôn phải trả về định dạng JSON để code Python có thể parse và thực thi.
*   **Human-in-the-Loop:** Đối với các lệnh giao dịch lớn hoặc cảnh báo đỏ, hệ thống luôn yêu cầu xác nhận từ người dùng qua Telegram/Web trước khi thực thi.

---

## 📈 3. Quy Trình Vận Hành A-Z (The Golden Flow)

1.  **CRON/Scheduler:** Tự động kích hoạt `etl` mỗi 15 phút.
2.  **ETL:** Thu thập dữ liệu thô -> Clean -> Lưu vào `data/finvista.db`.
3.  **Quant Engine:** Tính Greeks & G-Score cho toàn bộ thị trường.
4.  **Credit Engine:** Quét Red Flags & XGBoost Probability cho các mã đạt chuẩn Quant.
5.  **AI Committee:** Nếu mã lọt vào Top 10 -> Kích hoạt 7 lớp phân tích AI.
6.  **Debate & PM:** AI thảo luận và ra quyết định cuối cùng.
7.  **Delivery:** Đẩy thông báo qua Telegram và cập nhật Dashboard WebSockets.

---
*Bản thiết kế này là kim chỉ nam cho việc phát triển và mở rộng Finvista thành một nền tảng chuyên nghiệp.*
