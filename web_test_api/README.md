# FaceAccess Portal

Website nay dung API Python/FastAPI va Supabase that. Khong co mock, dang nhap email/password, camera gia lap hoac dong bo gia.

## Chay local

Trong thu muc `backend`:

```powershell
.\.venv\Scripts\python.exe run.py
```

Mo `http://127.0.0.1:5000/portal/`, bam **Ket noi**, nhap gia tri `BACKEND_API_KEY` trong `backend/.env`. Khong nhap `SUPABASE_SECRET_KEY`.

Portal va API cung origin. Khong can CORS, npm, frontend build hay web server rieng. Neu backend dang chay truoc khi them portal, khoi dong lai backend.

Key chi luu trong bo nho trang, khong luu localStorage/sessionStorage/cookie. Refresh trang hoac ngat ket noi se xoa key. Day la portal quan tri noi bo, khong phai trang dang nhap nguoi dung. Khong dua key quan tri cho nhan vien, khong public portal/API khi chua co phan quyen phu hop va HTTPS.

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
