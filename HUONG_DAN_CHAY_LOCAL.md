# 🚀 Hướng Dẫn Cấu Hình & Chạy Dự Án Finvista Tại Local

Tài liệu này hướng dẫn chi tiết các thành viên trong nhóm cách tải dữ liệu, cấu hình và khởi chạy ứng dụng **Finvista** trên máy cá nhân (Local).

---

## 🛠️ 1. Yêu Cầu Hệ Thống (Prerequisites)

Trước khi bắt đầu, hãy đảm bảo máy tính của bạn đã cài đặt:
1. **Python (phiên bản >= 3.9, khuyến nghị 3.10 hoặc 3.11)**
2. **Node.js (phiên bản >= 18)**
3. **Git**

---

## 📁 2. Các Bước Thiết Lập Dự Án

### Bước 1: Clone dự án về máy
Mở Terminal tại thư mục bạn muốn lưu dự án và chạy:
```bash
git clone <URL_KHO_LƯU_TRỮ_GITHUB>
cd Finvista
```

### Bước 2: Cấu hình Môi trường (`.env`)
Các tệp cấu hình chứa thông tin nhạy cảm đã bị ẩn khỏi GitHub để bảo mật. Bạn cần tạo tệp cấu hình riêng:
1. Copy file mẫu `.env.example` và đổi tên thành `.env`:
   - Trên Linux/macOS: `cp .env.example .env`
   - Trên Windows (PowerShell): `copy .env.example .env`
2. Mở file `.env` mới tạo và điền các API Key / Thông tin bảo mật do Trưởng nhóm (Host dự án) gửi riêng trong nhóm kín (Zalo/Telegram/Discord).

### Bước 3: Nạp thư mục dữ liệu (`data/`)
Thư mục `data/` chứa dữ liệu thị trường và mô hình học máy nặng nên đã bị loại khỏi Git.
1. Hãy truy cập đường link **Google Drive / OneDrive** do nhóm chia sẻ để tải file nén dữ liệu `data.zip` (hoặc thư mục dữ liệu).
2. Giải nén và đặt thư mục `data/` vào **thư mục gốc** của dự án (ngang hàng với file `run.py` và thư mục `frontend/`).
3. Đảm bảo cấu trúc thư mục dạng:
   ```text
   Finvista/
   ├── data/
   │   ├── finvista.db
   │   └── ... (các file csv/json khác)
   ├── frontend/
   ├── run.py
   └── ...
   ```

---

## 🚀 3. Khởi Chạy Ứng Dụng

Ứng dụng Finvista chạy theo kiến trúc Client-Server, do đó bạn cần mở **2 Terminal song song**:

### Terminal 1: Khởi chạy Backend API (Python)
1. Tạo môi trường ảo và cài đặt các thư viện Python:
   ```bash
   pip install -e .
   ```
2. Khởi chạy Backend API bằng lệnh:
   ```bash
   python run.py api
   ```
   *Khi chạy thành công, API sẽ chạy tại: `http://127.0.0.1:8008/docs` (tài liệu Swagger)*.

---

### Terminal 2: Khởi chạy Frontend UI (React + Vite)
1. Di chuyển vào thư mục frontend:
   ```bash
   cd frontend
   ```
2. Cài đặt các gói thư viện Node.js:
   ```bash
   npm install
   ```
3. Chạy frontend ở chế độ nhà phát triển (Development):
   ```bash
   npm run dev
   ```
   *Giao diện người dùng sẽ được khởi chạy tại: `http://127.0.0.1:5173/`*.

---

## 🔐 4. Đăng Nhập Hệ Thống

Khi mở trình duyệt và truy cập `http://127.0.0.1:5173/`, hệ thống sẽ yêu cầu đăng nhập. Bạn hãy điền thông tin tài khoản Demo sau:

- **Tên đăng nhập (Username):** `demo`
- **Mật khẩu (Password):** `finvista123`

Sau khi đăng nhập thành công, bạn có thể sử dụng đầy đủ các chức năng định giá chứng quyền và phân tích kiệt quệ tài chính!
