# FaceAccess Web Portal (React + Vite + Ant Design)

Cổng thông tin quản trị hiện đại cho hệ thống kiểm soát ra vào và nhận diện khuôn mặt. Được xây dựng trên nền tảng **React 19**, **Vite**, và **Ant Design v6**, kết nối trực tiếp với backend Python/FastAPI và cơ sở dữ liệu Supabase.

---

## 🚀 Hướng dẫn khởi chạy

### 1. Chuẩn bị Backend
Trước tiên, hãy đảm bảo Backend đang chạy tại `http://127.0.0.1:5000`:

```powershell
cd backend
.\.venv\Scripts\python.exe run.py
```

### 2. Cài đặt và chạy Web Portal
Mở một terminal mới:

```powershell
cd web_portal
npm install
npm run dev
```

Trình duyệt sẽ mở tại `http://localhost:3000/` (hoặc cổng hiển thị trên terminal). Vite đã được cấu hình proxy tự động chuyển tiếp toàn bộ yêu cầu `/api/v1/...` sang Backend `http://127.0.0.1:5000`.

### 3. Đăng nhập hệ thống
- **Tài khoản quản trị mặc định:** `admin`
- **Mật khẩu mặc định:** `admin123`
*(Hoặc có thể chuyển sang tab **API Key (Dev)** để kết nối trực tiếp bằng `BACKEND_API_KEY` từ file `backend/.env`)*.

---

## 🌟 Các tính năng chính (Kế thừa & Nâng cấp từ Web Test API)

| Phân hệ | Tính năng chi tiết |
|---|---|
| **Xác thực & Bảo mật** | - Đăng nhập Quản trị viên (`/auth/login`) với JWT token lưu trữ an toàn trong `sessionStorage`.<br>- Hỗ trợ kết nối nhà phát triển qua `x-api-key` (`/health`).<br>- Tự động kiểm tra phiên (`/auth/me`), tự động đăng xuất khi hết hạn hoặc 401.<br>- Route Guard thông minh: bảo vệ các trang quản trị. |
| **Tổng quan (Dashboard)** | - Thống kê số lượng Người dùng (Tổng / Đang hoạt động).<br>- Thống kê Thiết bị cửa (Tổng / Online / Cảnh báo).<br>- Theo dõi Phiên đăng ký đang chờ (Pending).<br>- Giám sát trạng thái kết nối Cloud Backend & Supabase Database thời gian thực.<br>- Bảng hoạt động ra vào gần nhất & Lối tắt thao tác nhanh. |
| **Quản lý Người dùng** | - Danh sách nhân sự với Avatar ký tự, Mã nhân viên, Phòng ban, Chức danh, Email, SĐT, Trạng thái (Hoạt động / Ngừng hoạt động).<br>- Tìm kiếm nhanh theo tên, mã NV, email; Lọc theo phòng ban và trạng thái.<br>- Thêm mới & Cập nhật người dùng với cơ chế dirty-check.<br>- Xem chi tiết thông tin.<br>- **Quản lý Vector khuôn mặt:** Xem thông tin vector đã lưu, nạp/cập nhật vector (Model name, version, dimension, mảng JSON số thực), sinh vector mẫu ngẫu nhiên để kiểm thử, xóa vector khuôn mặt. |
| **Quản lý Thiết bị (Edge Devices)** | - Danh sách thiết bị cửa, trạng thái kết nối (Online / Offline / Cảnh báo), vị trí lắp đặt, thời điểm hoạt động cuối.<br>- Cấu hình thông số nhận diện: Ngưỡng tin cậy (Threshold %), Thời gian mở cửa (giây), Bật/Tắt kiểm tra khuôn mặt thật (Liveness Detection).<br>- **Bảo mật Token:** Khi tạo thiết bị mới, hệ thống hiển thị mã `device_token` một lần duy nhất kèm cảnh báo và nút sao chép nhanh trước khi đóng. |
| **Phiên Đăng ký khuôn mặt** | - Danh sách phiên với trạng thái: Chờ đăng ký (Pending), Hoàn tất (Completed), Đã hủy (Cancelled), Hết hạn (Expired), Thất bại (Failed).<br>- Khởi tạo phiên: Chỉ cho phép chọn người dùng đang hoạt động (Active), chọn thiết bị tại cửa, cấu hình thời hạn phiên.<br>- Thao tác thông minh với phiên chờ: Nạp vector khuôn mặt trực tiếp, Hoàn tất phiên, Hủy phiên, Đánh dấu thất bại. |
| **Lịch sử Truy cập Cửa** | - Nhật ký kiểm soát cửa: Người dùng nhận diện, Thiết bị ghi nhận, Kết quả (Cho phép / Từ chối), Độ tin cậy (%) dạng thanh tiến trình trực quan, Thời điểm truy cập (giờ Việt Nam UTC+7), Thời điểm đồng bộ lên Cloud.<br>- Lọc theo Kết quả, Người dùng, Thiết bị.<br>- Ghi sự kiện thủ công / mô phỏng: Tự sinh mã UUIDv4 đảm bảo tính bất biến (idempotency). |

---

## 🛠️ Công nghệ sử dụng
- **React 19**
- **Vite 8**
- **Ant Design v6 (`antd`)** & **@ant-design/icons**
- **Day.js** cho xử lý ngày giờ
- Kiến trúc Modular Feature-based (`src/app/features/*`, `src/app/services/*`, `src/app/layouts/*`, `src/app/providers/*`)
