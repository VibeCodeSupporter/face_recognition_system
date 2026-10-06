# FaceAccess: schema tối giản để test

Bản đang dùng có **5 bảng Cloud + 3 bảng Edge**, giảm từ **23 xuống 8 bảng**
(khoảng **65%**, gần 2/3). Riêng Cloud giảm đúng 2/3: từ 15 còn 5 bảng.
Sơ đồ chỉ còn **2 trang**, tập trung vào các luồng test hiện có trong project.

## File

- `faceaccess_database_schema.drawio`: file chính, chỉnh sửa được trong draw.io.
- `cloud_schema.dbml`, `edge_schema.dbml`: định nghĩa tương ứng với bản tối giản.
- `preview/01-cloud-mvp.png`, `preview/02-edge-mvp.png`: ảnh xem nhanh.
- `archive/full-version/`: bản đầy đủ trước đây, giữ riêng để tham khảo khi mở rộng.
- `supabase/`: script SQL riêng cho từng bảng Cloud và ví dụ thêm cột/dữ liệu.
  Chạy theo thứ tự trong `supabase/README.md`; chưa áp dụng lên database trực tuyến.

Mở file bằng draw.io Desktop hoặc diagrams.net: **File > Open From > Device**.
Không tạo PDF. Đây là bản thiết kế; chưa chạy migration hoặc đổi API/database thật.

## Năm bảng Cloud

| Bảng | Dùng để test |
| --- | --- |
| `users` | Thông tin và trạng thái người dùng |
| `devices` | Thiết bị/cửa, heartbeat và cấu hình nhỏ trong `settings` JSON |
| `face_embeddings` | Gộp đường dẫn ảnh và vector; mỗi người có một template hiện tại |
| `registration_sessions` | Tạo phiên, hoàn tất, hủy và hết hạn đăng ký khuôn mặt |
| `access_logs` | Nhật ký cho phép/từ chối, gồm cả người lạ |

`face_embeddings.user_id` vừa là PK vừa là FK tới `users.id`: đăng ký lại
thay thế template cũ bằng UPSERT. Giữ `model_name`, `model_version` và
`dimension` để nhận diện không so khớp vector thuộc các model khác nhau.

Cấu hình ví dụ trong `devices.settings`:

```json
{"threshold": 80, "doorDuration": 3, "liveness": true}
```

Ứng dụng kiểm tra các key và kiểu giá trị của cấu hình. Cấu hình mặc định lấy
từ code/env; khi chỉnh qua Portal thì lưu object tương ứng trên thiết bị được chọn.

**Quy tắc demo:** người dùng active, đã đăng ký, đạt ngưỡng nhận diện và kiểm
tra liveness khi bật thì được dùng mọi cửa trong hệ thống test. Chưa giới hạn
quyền theo từng cửa. Đăng nhập quản trị dùng cơ chế hiện có/Supabase Auth;
chưa bổ sung bảng RBAC cho ứng dụng.

## Ba bảng Edge

| Bảng | Vai trò |
| --- | --- |
| `local_users` | Cache người dùng và template trong cùng một dòng |
| `local_device` | Một dòng lưu UUID, tên, cấu hình và lần đồng bộ của thiết bị |
| `local_access_logs` | Lịch sử offline đồng thời làm hàng đợi gửi lại |

`local_users.face_template_json` chứa `model_name`, `model_version`,
`dimension`, `embedding_data`; NULL nếu chưa có template. UUID khớp với Cloud.
SQLite lưu JSON dưới dạng TEXT và timestamp UTC ISO 8601.

Để test với ít dữ liệu, tải **snapshot đầy đủ** của users + templates rồi
thay cache trong một giao dịch. Tạm chưa dùng cursor, incremental sync hay tombstone.
Không đụng vào nhật ký offline khi thay cache.

Log sinh UUID ngay khi nhận diện. Gửi các dòng có `synced_at IS NULL`;
Cloud khử trùng theo `access_logs.id`. Chỉ đánh dấu đã gửi sau ACK xác nhận
Cloud đã commit; mất ACK thì gửi lại cùng UUID. Như vậy không cần outbox riêng.
`local_access_logs.user_id` và `device_id` là định danh lịch sử, cố ý không
ràng buộc FK tới cache có thể thay thế.

Luồng tạo phiên/đăng ký mới cần kết nối Cloud ở giai đoạn này. Offline chỉ
phục vụ nhận diện từ cache và ghi log; thêm đăng ký offline khi cần.

## Phần để sau

Chưa thêm các bảng tài khoản/vai trò/quyền Portal, quyền cửa, cấu hình override,
checkpoint, hàng đợi restart/sync, outbox hay phiên đăng ký offline.
Ảnh khuôn mặt và embedding được gộp; chưa lưu nhiều góc chụp hoặc nhiều model
cùng lúc cho một người. Snapshot, chất lượng ảnh, MAC/IP/firmware và các trường
audit nâng cao có thể bổ sung khi phát sinh nhu cầu.

Khi mở rộng, ưu tiên bảng quyền cửa và tách template theo model/ảnh nếu cần.
Bản cũ trong `archive/full-version/` có các chi tiết đó để đối chiếu.

## Ghép với API hiện tại

- `USR001`, `DEV001` là mã nghiệp vụ; FK dùng UUID nội bộ.
- `name`, `dept` ánh xạ từ `full_name`, `department`; giữ phone và chức danh
  `role` để form người dùng hiện tại vẫn có dữ liệu.
- `faceStatus` được tính từ template: có template là enrolled; chưa có thì
  failed nếu phiên gần nhất thất bại, còn lại là pending.
- `requestBy`, IP/firmware/uptime và số liệu hiển thị chưa có cột trong bản này;
  API trả giá trị trống/phù hợp khi tích hợp. Tên user/cửa trong log lấy bằng JOIN.
- `lastAccess`, `totalToday` tính từ `access_logs`; không lưu thêm bản sao.
- Backend kiểm tra trạng thái/thời hạn phiên trước khi ghi template và đổi phiên
  sang completed trong cùng giao dịch. Kiểm tra vector là mảng số đúng dimension.
- Không xóa cascade vào access logs; đổi user sang inactive nếu đã có lịch sử.
  Timestamp dùng UTC, frontend định dạng theo Asia/Ho_Chi_Minh.

## Tạo lại sơ đồ

```powershell
python docs/database_schema/generate_schema.py --dot "C:/Program Files/Graphviz/bin/dot.exe"
```

Script chỉ tạo lại bản tối giản và các ảnh trong `preview/`; bản lưu trong
`archive/full-version/` không bị ghi đè. PK, FK, kích thước và tham chiếu XML
được kiểm tra khi tạo file. Chỉnh tay trong draw.io nên giữ bản riêng vì chạy
script sẽ bố trí lại sơ đồ từ nguồn.
