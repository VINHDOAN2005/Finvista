# 🚀 Hướng Dẫn Cấu Hình & Chạy Dự Án Finvista Tại Local (Cầm Tay Chỉ Việc)

Tài liệu này hướng dẫn chi tiết từng bước (kể cả những bạn không rành công nghệ hay Git) cách tải dữ liệu, cấu hình các mã bảo mật và chạy dự án **Finvista** dưới máy cá nhân.

---

## 🛠️ 1. Cài Đặt Công Cụ Ban Đầu (Chỉ Cần Làm 1 Lần)

Trước khi chạy dự án, hãy tải và cài đặt 3 công cụ sau lên máy tính:
1. **Python (Chọn phiên bản 3.10 hoặc 3.11):** 
   - Tải về tại: [https://www.python.org/downloads/](https://www.python.org/downloads/)
   - *⚠️ LƯU Ý QUAN TRỌNG:* Khi chạy file cài đặt, nhớ tích chọn vào ô **"Add Python to PATH"** ở dưới cùng trước khi bấm Install.
2. **Node.js (Chọn bản LTS mới nhất):**
   - Tải về tại: [https://nodejs.org/](https://nodejs.org/) (chỉ cần bấm Next liên tục đến khi hoàn thành).
3. **Git (Công cụ quản lý code):**
   - Tải về tại: [https://git-scm.com/](https://git-scm.com/)

---

## 📁 2. Tải Dự Án & Thiết Lập Cấu Hình (Từng Bước Một)

### Bước 1: Tải mã nguồn dự án về máy
Bạn có thể chọn **1 trong 2 cách** sau:

* **Cách A (Nếu KHÔNG biết dùng Git):**
  1. Truy cập vào trang GitHub chứa dự án.
  2. Bấm vào nút màu xanh lá **Code** ở góc trên bên phải.
  3. Chọn **Download ZIP**.
  4. Sau khi tải xong, click chuột phải vào file `.zip` vừa tải về, chọn **Extract Here** (hoặc Giải nén) ra một thư mục trên máy tính.

* **Cách B (Nếu biết dùng Git):**
  1. Mở Command Prompt (cmd) hoặc Terminal trên máy.
  2. Di chuyển đến thư mục bạn muốn lưu dự án rồi chạy lệnh:
     ```bash
     git clone <ĐƯỜNG_LINK_GITHUB_DỰ_ÁN>
     cd Finvista
     ```

---

### Bước 2: Tạo và điền mã khóa bảo mật (`.env`)
Vì vấn đề bảo mật, các mã khóa kết nối và API Key đã được ẩn đi. Bạn cần tạo file này thủ công:
1. Truy cập vào thư mục dự án vừa giải nén, tìm file có tên là `.env.example`.
2. Click chuột phải vào file `.env.example`, chọn **Copy** (hoặc ấn `Ctrl + C`), sau đó bấm **Paste** (`Ctrl + V`) ngay tại đó để tạo bản sao.
3. Bản sao mới tạo thường có tên là `.env.example - Copy` hoặc tương tự. Hãy click chuột phải vào file đó, chọn **Rename** (Đổi tên) thành đúng chữ: `.env`
   - *⚠️ Lưu ý:* File chỉ có tên là `.env` (bắt đầu bằng dấu chấm), không được có đuôi `.txt` hay bất cứ gì khác đằng sau.
4. Click chuột phải vào file `.env` vừa đổi tên, chọn **Open with** (Mở bằng) -> chọn **Notepad** (Sổ ghi chép có sẵn trên Windows) hoặc **VS Code**.
5. Bạn sẽ thấy danh sách các biến để trống. Hãy copy các mã key mà trưởng nhóm gửi trong **nhóm chat kín** dán đè vào phần giá trị tương ứng (ví dụ: dán liên kết cơ sở dữ liệu sau dấu `=` của `DATABASE_URL=...`).
6. Nhấn **Ctrl + S** để lưu file lại và tắt đi.

---

### Bước 3: Nạp thư mục dữ liệu (`data/`)
Dữ liệu của hệ thống khá nặng nên được lưu trữ riêng biệt trên đám mây.
1. Hãy vào đường link **Google Drive / OneDrive** mà nhóm đã gửi.
2. Tải file nén dữ liệu (thường có tên là `data.zip` hoặc thư mục `data`) về máy.
3. Giải nén file vừa tải về, bạn sẽ nhận được một thư mục có tên là `data`.
4. Copy/di chuyển thư mục `data` này thả vào **thư mục gốc của dự án** (đặt nằm ngang hàng với file `run.py` và thư mục `frontend`).
5. Đảm bảo cấu trúc các file trông như sau:
   ```text
   Finvista/ (Thư mục dự án của bạn)
   ├── data/  <-- Thư mục bạn vừa thả vào
   │   ├── finvista.db
   │   └── ...
   ├── frontend/
   ├── run.py
   └── ...
   ```

---

## 🚀 3. Cách Khởi Chạy Ứng Dụng

Hệ thống cần khởi chạy cả Backend (xử lý dữ liệu) và Frontend (giao diện) đồng thời. Bạn hãy làm theo các bước mở **2 cửa sổ Terminal** dưới đây:

### Terminal 1: Chạy Backend (Python)
1. Mở thư mục dự án trên máy tính.
2. Click chuột trái vào **thanh địa chỉ** ở trên cùng của thư mục (nơi hiển thị đường dẫn thư mục, ví dụ: `D:\Projects\Finvista`), gõ chữ `cmd` rồi nhấn **Enter**.
3. Cửa sổ Command Prompt (màu đen) sẽ xuất hiện. Bạn gõ lệnh sau để cài đặt thư viện cần thiết:
   ```bash
   pip install -e .
   ```
   *(Nhấn Enter và đợi khoảng 1-2 phút cho chương trình cài đặt hoàn tất).*
4. Sau khi cài xong, gõ tiếp lệnh sau để khởi chạy máy chủ API:
   ```bash
   python run.py api
   ```
   *(Nhấn Enter. Giữ nguyên cửa sổ này, không được tắt đi).*

---

### Terminal 2: Chạy Giao diện Frontend (React)
1. Quay lại cửa sổ thư mục dự án. Click chuột trái vào thanh địa chỉ trên cùng một lần nữa, gõ chữ `cmd` và nhấn **Enter** để mở thêm một cửa sổ màu đen thứ hai.
2. Ở cửa sổ đen thứ hai này, di chuyển vào thư mục frontend bằng cách gõ:
   ```bash
   cd frontend
   ```
   *(Nhấn Enter)*.
3. Cài đặt các thư viện giao diện bằng cách gõ:
   ```bash
   npm install
   ```
   *(Nhấn Enter và đợi chạy cài đặt xong)*.
4. Cuối cùng, chạy giao diện bằng lệnh:
   ```bash
   npm run dev
   ```
   *(Nhấn Enter)*. 
5. Lúc này, trên màn hình sẽ xuất hiện một đường link dạng `http://127.0.0.1:5173/`. Bạn chỉ cần giữ phím **Ctrl** và click chuột trái vào link đó (hoặc copy dán vào Google Chrome/Microsoft Edge) là giao diện web sẽ mở lên!

---

## 🔐 4. Đăng Nhập Tài Khoản

Khi giao diện web hiện ra, hệ thống yêu cầu thông tin đăng nhập. Bạn hãy điền chính xác thông tin sau:

- **Tên đăng nhập (Username):** `demo`
- **Mật khẩu (Password):** `finvista123`

Chúc các bạn khởi chạy dự án thành công! Nếu gặp bất kỳ lỗi nào liên quan đến thư viện hoặc cài đặt, hãy chụp ảnh màn hình gửi lên nhóm chat để được hỗ trợ.
