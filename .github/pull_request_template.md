## 📌 Description

Thiết lập **Database Schema** hoàn chỉnh cho Supabase và xây dựng **Backend API** (Python FastAPI) phiên bản MVP đầu tiên.
Đồng thời bổ sung **Web Test API Portal** để kiểm thử các endpoint từ trình duyệt và gộp `.gitignore` về root.

> **Jira:** [FRS-5] Add Demo Database schema and API test ver 1

## 🔄 Changes

### 1. Database Schema & Docs (`docs/database_schema/`)
- Thiết kế schema cho 5 bảng chính: `users`, `devices`, `face_embeddings`, `access_logs`, `registration_sessions`.
- Thêm SQL migration scripts cho Supabase: [`docs/database_schema/supabase/`](https://github.com/VibeCodeSupporter/face_recognition_system/tree/webserver_thanhdat/docs/database_schema/supabase) (từ `00_setup.sql` → `06_verify_schema.sql`).
- Thêm drawio diagram + preview PNG/SVG: [`docs/database_schema/preview/`](https://github.com/VibeCodeSupporter/face_recognition_system/tree/webserver_thanhdat/docs/database_schema/preview).
- Tài liệu hướng dẫn: [`docs/database_schema/README.md`](https://github.com/VibeCodeSupporter/face_recognition_system/blob/webserver_thanhdat/docs/database_schema/README.md).

### 2. Backend FastAPI (`backend/`)
- Cấu trúc lại backend theo kiến trúc **Controller → Service → Repository**:
  - [`app/controllers.py`](https://github.com/VibeCodeSupporter/face_recognition_system/blob/webserver_thanhdat/backend/app/controllers.py) – Định nghĩa API routes.
  - [`app/services.py`](https://github.com/VibeCodeSupporter/face_recognition_system/blob/webserver_thanhdat/backend/app/services.py) – Business logic.
  - [`app/repositories.py`](https://github.com/VibeCodeSupporter/face_recognition_system/blob/webserver_thanhdat/backend/app/repositories.py) – Tương tác database (Supabase).
  - [`app/dto/`](https://github.com/VibeCodeSupporter/face_recognition_system/tree/webserver_thanhdat/backend/app/dto) – Data Transfer Objects (Pydantic models).
  - [`app/infrastructure/database.py`](https://github.com/VibeCodeSupporter/face_recognition_system/blob/webserver_thanhdat/backend/app/infrastructure/database.py) – Kết nối Supabase.
  - [`app/middleware.py`](https://github.com/VibeCodeSupporter/face_recognition_system/blob/webserver_thanhdat/backend/app/middleware.py) – Error handling & logging middleware.
- Thêm scripts tiện ích: [`scripts/`](https://github.com/VibeCodeSupporter/face_recognition_system/tree/webserver_thanhdat/backend/scripts) (`check_database.py`, `seed_users.py`, `request_api.py`).
- Thêm Dockerfile & `.env.example` cho deploy.
- Hướng dẫn chi tiết: [`backend/README.md`](https://github.com/VibeCodeSupporter/face_recognition_system/blob/webserver_thanhdat/backend/README.md).

### 3. Web Test API Portal (`web_test_api/`)
- Trang web tĩnh để test các API endpoint trực tiếp từ trình duyệt.
- Gồm form gửi request cho Users, Devices, Access Logs, v.v.
- Chi tiết: [`web_test_api/README.md`](https://github.com/VibeCodeSupporter/face_recognition_system/blob/webserver_thanhdat/web_test_api/README.md).

### 4. Cấu hình chung
- Gộp `backend/.gitignore` vào [`.gitignore`](https://github.com/VibeCodeSupporter/face_recognition_system/blob/webserver_thanhdat/.gitignore) ở root (xoá file `.gitignore` riêng trong `backend/`).
- Xoá `docker-compose.yml` và `web/` cũ (đã thay bằng `web_test_api/`).

## 🧪 Testing

- Chạy test tại local bằng scripts: `python -m scripts.check_database` và `python -m scripts.request_api`.
- Kiểm thử API thủ công qua **Web Test API Portal** (`web_test_api/index.html`).
- Test tự động: [`tests/test_integration.py`](https://github.com/VibeCodeSupporter/face_recognition_system/blob/webserver_thanhdat/backend/tests/test_integration.py), [`tests/test_commands.py`](https://github.com/VibeCodeSupporter/face_recognition_system/blob/webserver_thanhdat/backend/tests/test_commands.py).

* [x] Tested locally
* [x] Manual test
* [ ] Unit test
* [ ] Integration test

## 📸 Screenshots / Demo

### Cloud MVP – Database Schema
![Cloud MVP Database Schema](docs/database_schema/preview/01-cloud-mvp.png)

### Edge MVP – Database Schema
![Edge MVP Database Schema](docs/database_schema/preview/02-edge-mvp.png)

## ⚠️ Notes

- Cần tạo file `.env` từ [`backend/.env.example`](https://github.com/VibeCodeSupporter/face_recognition_system/blob/webserver_thanhdat/backend/.env.example) với Supabase credentials thực tế trước khi chạy.
- Các SQL scripts cần chạy theo thứ tự (`00` → `06`) trên Supabase SQL Editor.
- Web Test API Portal yêu cầu backend đang chạy tại `localhost:8000`.

## ✅ Checklist

* [x] Code đã được test
* [x] Không commit secret / API key / password
* [x] Đã cập nhật documentation nếu cần
* [ ] Không có lỗi lint / format
* [ ] Không có file không cần thiết
* [x] PR này chỉ chứa những thay đổi liên quan
