# Finvista Local Web Demo Frontend

Frontend React + Vite chạy local và gọi Backend FastAPI của Finvista tại `http://127.0.0.1:8008`.

## Chạy nhanh

Từ thư mục gốc repo:

```powershell
cd D:\Finvista
.\Start_Finvista_Web.bat
```

Sau đó mở:

```text
http://127.0.0.1:5173/
```

## Chạy thủ công

```powershell
cd D:\Finvista\frontend
$env:Path = "D:\Node.js;" + $env:Path
& "D:\Node.js\npm.cmd" run dev
```

## Backend

Backend cần chạy riêng ở terminal khác:

```powershell
cd D:\Finvista
python -m uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8008
```

Hoặc chạy file có sẵn:

```powershell
.\Start_Finvista_API.bat
```

Swagger:

```text
http://127.0.0.1:8008/docs
```

## Cấu hình API URL

App có fallback mặc định:

```text
http://127.0.0.1:8008
```

Nếu cần đổi, tạo file `.env` từ `.env.example`:

```powershell
Copy-Item .env.example .env
```

Nội dung:

```env
VITE_API_BASE_URL=http://127.0.0.1:8008
```

Không đưa Telegram token, API key hoặc secret vào frontend.
