# FaceAccess Portal

Website nay dung API Python/FastAPI va Supabase that. Khong co mock, dang nhap email/password, camera gia lap hoac dong bo gia.

## Chạy local

Trong thư mục `backend`:

```powershell
.\.venv\Scripts\python.exe run.py
```

Mở trình duyệt trực tiếp tại `http://127.0.0.1:5000/` (hoặc `http://localhost:5000/`).

Website sẽ hiển thị cửa sổ **Đăng nhập Quản trị viên**:
- **Tên đăng nhập mặc định:** `admin`
- **Mật khẩu mặc định:** `admin123`
*(Có thể tùy chỉnh tài khoản trong file `backend/.env` qua `ADMIN_USERNAME` và `ADMIN_PASSWORD`)*

Sau khi đăng nhập thành công, bạn có toàn quyền quản trị người dùng, thiết bị, phiên đăng ký và lịch sử ra vào mà không cần chạy server riêng hay nhập chuỗi API key phức tạp.
(Nếu là lập trình viên muốn dùng trực tiếp API key, có thể bấm liên kết "Kết nối qua Backend API Key").

## API duoc su dung

- Users: GET `/users` (data la mang, chi loc status/department), GET/POST/PATCH/DELETE users. Phan trang tren web la phan trang local sau khi backend tra tat ca.
- Devices: GET/POST/PATCH/DELETE; settings chi gom threshold, doorDuration, liveness. Token hien mot lan khi tao, can luu truoc khi dong cua so.
- Registration sessions: GET/POST/PATCH/DELETE `/registration-sessions`. Chi pending, chua het han moi duoc ket thuc; completed can vector da luu. Luu vector va hoan tat phien la hai thao tac rieng.
- Face embeddings: GET/PUT/DELETE `/users/{id}/face-embedding`. Chi nhap vector do model that tao, khong tao vector gia tu camera.
- Access logs: GET/POST. Khong sua/xoa lich su. UUID su kien khong doi khi gui lai form, backend kiem tra idempotency.

Web su dung dung ten cot trong DTO. UUID/timestamps sinh tu backend khong nam trong form users/devices. `role` la chuc danh, khong phai quyen truy cap. Gio hien thi la Asia/Ho_Chi_Minh den giay; database van giu do chinh xac goc. Truong datetime-local trong form duoc chuyen tu gio may sang ISO UTC khi gui.

## Loi va kiem tra

Form kiem tra required, do dai, email, so, dimension/vector va thoi han phien. Backend van la noi quyet dinh tinh hop le. Loi 400/401/404/409/413/422/500/503 hien thong bao va request ID, khong thay the bang du lieu mau. Khi request luu bi timeout, tai lai de xac nhan truoc khi gui lai. Cac thao tac luu/xoa khong tu dong retry.

GET users cua backend dang doc tat ca theo nhieu luot; du lieu lon se cham va khong co snapshot nguyen tu neu du lieu thay doi trong luc doc.

Chay test backend khong ghi du lieu:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Test ghi du lieu that chi chay khi `INTEGRATION_ALLOW_WRITES=true`, tao fixture rieng va don dep. Xem `backend/tests` de kiem tra ca portal.

## Nginx

Neu serve website rieng bang Nginx, `/api/` phai proxy ve backend, giu header x-api-key cua request. Cau hinh `nginx.conf` mac dinh dung backend:5000; HOST cua backend trong container phai la 0.0.0.0. Khong inject Supabase secret hoac backend key vao static files.
