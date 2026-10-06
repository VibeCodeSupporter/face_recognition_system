# SQL để paste vào Supabase

Các file này tạo **đúng 5 bảng Cloud** của bản draw.io tối giản. Ba bảng Edge
là SQLite trên thiết bị, không tạo trên Supabase. Chưa chạy script lên tài khoản
Supabase của bạn.

Đã kiểm tra bằng PostgreSQL cục bộ (PGlite): tạo bảng khớp các cột trong draw.io,
UPSERT vector, từ chối vector sai, FK, chống trùng log, timestamp, quyền truy cập
và các file ví dụ. 31 kiểm tra đã pass; chưa chạy trên project Supabase thực tế.

## Chạy theo thứ tự

Tạo/chọn project Supabase của bạn. Mỗi project đã có database PostgreSQL,
thường tên `postgres`; không cần chạy `CREATE DATABASE`. Các bảng nằm trong `public`.

Trong Dashboard, mở **SQL Editor > New query**, mở một file dưới đây,
paste toàn bộ nội dung vào query rồi chọn **Run**. Làm lần lượt:

| Thứ tự | File | Nội dung |
| --- | --- | --- |
| 0 | `00_setup.sql` | Hai hàm nhỏ: tự cập nhật timestamp và kiểm tra vector |
| 1 | `01_users.sql` | Bảng người dùng |
| 2 | `02_devices.sql` | Bảng thiết bị |
| 3 | `03_face_embeddings.sql` | Bảng lưu ảnh/vector khuôn mặt |
| 4 | `04_registration_sessions.sql` | Bảng phiên đăng ký |
| 5 | `05_access_logs.sql` | Bảng nhật ký ra vào |
| 6 | `06_verify_schema.sql` | Query kiểm tra bảng, cột, khóa và RLS |

Mỗi file tạo bảng nằm trong một giao dịch: lỗi thì các thay đổi của file đó
không được commit. Các file CREATE TABLE dùng cho bảng **chưa tồn tại**.
Nếu báo `relation already exists`, không xóa bảng hoặc chạy lại để cập nhật;
dùng migration `ALTER TABLE`. Nếu project đã chạy SQL cũ trong
`docs/cloud_database_schema.sql`, cần đối chiếu cấu trúc cũ trước khi migration.

## Vector lưu ở đâu?

**`public.face_embeddings.embedding_data`**, kiểu JSONB, là mảng số.
`user_id` liên kết tới `users.id` và cũng là khóa chính, nên mỗi người có
**một template hiện tại**. Đăng ký lại dùng `INSERT ... ON CONFLICT (user_id)
DO UPDATE` để thay template. `image_url` chỉ lưu đường dẫn ảnh tùy chọn.

Điền model thực tế vào `model_name`, `model_version` và số chiều vào `dimension`.
Ví dụ model 512 chiều thì mảng phải chứa đúng 512 số. Constraint từ chối mảng
sai độ dài, chuỗi, null trong mảng hoặc giá trị không phải mảng. Không cần cài
pgvector cho bước lưu và đồng bộ này; nhận diện vẫn thực hiện tại Edge.

Ví dụ chạy được nằm trong `examples/03_save_or_replace_vector.sql`.
Vector 4 số trong file **chỉ là dữ liệu giả để kiểm tra việc lưu**, không dùng
để nhận diện. Khi đăng ký thật, backend kiểm tra phiên pending, đúng user/device,
chưa hết hạn, rồi ghi template và cập nhật phiên completed/completed_at trong
cùng giao dịch. File ví dụ chỉ minh họa thao tác ghi template trực tiếp.

## Thêm cột, thuộc tính và hàng

| Bạn cần làm | Câu lệnh | File ví dụ |
| --- | --- | --- |
| Thêm cột mới | `ALTER TABLE ... ADD COLUMN ...` | `examples/01_add_column.sql` |
| Thêm hàng dữ liệu | `INSERT INTO ... VALUES ...` | `examples/02_insert_test_rows.sql` |
| Thay vector của người đã có | `INSERT ... ON CONFLICT ... DO UPDATE` | `examples/03_save_or_replace_vector.sql` |
| Đổi dữ liệu của một hàng | `UPDATE ... SET ... WHERE ...` | `examples/04_update_attributes.sql` |
| Thêm thuộc tính trong settings JSON | `settings = settings || '{...}'::jsonb` | `examples/04_update_attributes.sql` |

Các file trong `examples/` **không bắt buộc** để tạo schema. File 01 thêm cột
`users.note`; chỉ chạy nếu cần. File 02 tạo `TEST001`, `TESTDEV001` và một phiên
đăng ký; token thiết bị trong ví dụ chỉ phục vụ test. Chạy 02 trước 03 và 04.

Khi thêm cột, tạo file migration mới theo thứ tự ngày/số, ví dụ
`migrations/001_add_user_note.sql`, chạy một lần và giữ lại trong Git. Cập nhật
định nghĩa trong `generate_schema.py` rồi tạo lại draw.io/DBML, hoặc chỉnh sơ đồ
bằng tay. **Thêm cột trên draw.io không thay đổi database và ngược lại.**
Thêm hàng bằng INSERT không cần thay đổi sơ đồ. Thêm key JSON không cần thêm cột.
UPDATE luôn có WHERE để chọn đúng hàng cần đổi.

## Kết nối backend khi test

Mỗi bảng đã bật RLS; quyền Data API cho `anon`/`authenticated` bị thu hồi.
Bạn vẫn thao tác được từ SQL Editor với quyền quản trị. Backend dùng
`service_role`/client `supabaseAdmin` đã khai báo trong
`backend/src/config/supabase.js`. Client `supabase` dùng anon key hiện tại
sẽ không đọc được các bảng này; khi tích hợp endpoint, chọn client backend
phù hợp sau khi xác thực request. Không đưa service-role key vào frontend/Edge.

`users.id` là người được nhận diện, **không phải** `auth.users.id`. Vì vậy chưa
tạo policy kiểu `auth.uid() = users.id`. Cách này giữ schema nhỏ để test qua
backend mà không cần bảng quyền mới. Các script không thay đổi code endpoint.

`access_logs.id` không có UUID default: Edge phải sinh một UUID một lần và
dùng lại khi retry. Cloud ghi bằng `ON CONFLICT (id) DO NOTHING`. Không xóa
cascade vào nhật ký; người có lịch sử nên chuyển sang `inactive`.

Tài liệu tham khảo:
[Supabase: bảng và dữ liệu](https://supabase.com/docs/guides/database/tables),
[Supabase: RLS](https://supabase.com/docs/guides/database/postgres/row-level-security).
