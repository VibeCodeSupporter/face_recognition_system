import argparse
import random
import re
import sys
import unicodedata
from typing import List, Dict, Any

from app.config import ConfigurationError, load_settings
from app.errors import AppError
from app.infrastructure.database import Database

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


# Danh sách Họ, Tên đệm và Tên tiếng Việt thực tế
HO_LIST = [
    "Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Huỳnh", "Phan", "Vũ", "Võ",
    "Đặng", "Bùi", "Đỗ", "Hồ", "Ngô", "Dương", "Lý", "Đinh", "Đoàn"
]

DEM_NAM = ["Văn", "Đức", "Minh", "Quang", "Hữu", "Tuấn", "Thanh", "Quốc", "Duy", "Hoàng", "Bảo", "Trọng"]
TEN_NAM = ["An", "Bình", "Cường", "Dũng", "Đạt", "Hải", "Hiếu", "Hùng", "Huy", "Khoa", "Kiên", "Long", "Nam", "Nghĩa", "Phúc", "Quân", "Sơn", "Thắng", "Thịnh", "Toàn", "Trung", "Tú", "Việt"]

DEM_NU = ["Thị", "Thu", "Mai", "Ngọc", "Phương", "Thanh", "Bích", "Hồng", "Kim", "Mỹ", "Quỳnh", "Ánh"]
TEN_NU = ["Anh", "Châu", "Dung", "Hà", "Hằng", "Hiền", "Hoa", "Hương", "Lan", "Linh", "Mai", "Nga", "Ngọc", "Nhung", "Oanh", "Phương", "Thảo", "Trang", "Trâm", "Tuyết", "Vân", "Yến"]

# Đầu số di động Việt Nam (Viettel, VinaPhone, MobiFone)
PHONE_PREFIXES = [
    "098", "097", "096", "086", "038", "039", "037", "035",  # Viettel
    "091", "094", "088", "083", "085", "081",                 # VinaPhone
    "090", "093", "089", "070", "079", "077"                  # MobiFone
]

# Cơ cấu phòng ban và phân bổ số lượng nhân sự thực tế cho công ty 50 người
COMPANY_STRUCTURE = [
    # Ban Giám đốc (3 người)
    ("Ban Giám đốc", "Tổng Giám đốc (CEO)"),
    ("Ban Giám đốc", "Giám đốc Công nghệ (CTO)"),
    ("Ban Giám đốc", "Giám đốc Vận hành (COO)"),

    # Phòng Kỹ thuật & Công nghệ (16 người)
    ("Phòng Kỹ thuật & Công nghệ", "Trưởng phòng Kỹ thuật"),
    ("Phòng Kỹ thuật & Công nghệ", "Phó phòng Kỹ thuật"),
    ("Phòng Kỹ thuật & Công nghệ", "Kỹ sư Backend Cấp cao"),
    ("Phòng Kỹ thuật & Công nghệ", "Kỹ sư Backend"),
    ("Phòng Kỹ thuật & Công nghệ", "Kỹ sư Backend"),
    ("Phòng Kỹ thuật & Công nghệ", "Kỹ sư Frontend Cấp cao"),
    ("Phòng Kỹ thuật & Công nghệ", "Kỹ sư Frontend"),
    ("Phòng Kỹ thuật & Công nghệ", "Kỹ sư Frontend"),
    ("Phòng Kỹ thuật & Công nghệ", "Kỹ sư Trí tuệ Nhân tạo (AI)"),
    ("Phòng Kỹ thuật & Công nghệ", "Kỹ sư Trí tuệ Nhân tạo (AI)"),
    ("Phòng Kỹ thuật & Công nghệ", "Kỹ sư Hệ thống Nhúng"),
    ("Phòng Kỹ thuật & Công nghệ", "Kỹ sư Hệ thống Nhúng"),
    ("Phòng Kỹ thuật & Công nghệ", "Chuyên viên DevOps & Cloud"),
    ("Phòng Kỹ thuật & Công nghệ", "Chuyên viên Quản trị Cơ sở Dữ liệu"),
    ("Phòng Kỹ thuật & Công nghệ", "Kỹ sư Đảm bảo Chất lượng (QA/QC)"),
    ("Phòng Kỹ thuật & Công nghệ", "Kỹ sư Kiểm thử Phần mềm (Tester)"),

    # Phòng Kinh doanh (11 người)
    ("Phòng Kinh doanh", "Trưởng phòng Kinh doanh"),
    ("Phòng Kinh doanh", "Phó phòng Kinh doanh"),
    ("Phòng Kinh doanh", "Trưởng nhóm Kinh doanh B2B"),
    ("Phòng Kinh doanh", "Chuyên viên Kinh doanh Dự án"),
    ("Phòng Kinh doanh", "Chuyên viên Kinh doanh Dự án"),
    ("Phòng Kinh doanh", "Chuyên viên Phát triển Thị trường"),
    ("Phòng Kinh doanh", "Chuyên viên Phát triển Thị trường"),
    ("Phòng Kinh doanh", "Chuyên viên Tư vấn Giải pháp"),
    ("Phòng Kinh doanh", "Chuyên viên Tư vấn Giải pháp"),
    ("Phòng Kinh doanh", "Chuyên viên Chăm sóc Khách hàng Doanh nghiệp"),
    ("Phòng Kinh doanh", "Nhân viên Kinh doanh"),

    # Phòng Marketing & Truyền thông (5 người)
    ("Phòng Marketing & Truyền thông", "Trưởng phòng Marketing"),
    ("Phòng Marketing & Truyền thông", "Chuyên viên Digital Marketing"),
    ("Phòng Marketing & Truyền thông", "Chuyên viên Sáng tạo Nội dung"),
    ("Phòng Marketing & Truyền thông", "Chuyên viên Thiết kế Đồ họa (UI/UX)"),
    ("Phòng Marketing & Truyền thông", "Chuyên viên Truyền thông & Sự kiện"),

    # Phòng Kế toán - Tài chính (4 người)
    ("Phòng Kế toán - Tài chính", "Kế toán trưởng"),
    ("Phòng Kế toán - Tài chính", "Kế toán tổng hợp"),
    ("Phòng Kế toán - Tài chính", "Kế toán thanh toán & Công nợ"),
    ("Phòng Kế toán - Tài chính", "Chuyên viên Phân tích Tài chính"),

    # Phòng Nhân sự & Hành chính (4 người)
    ("Phòng Nhân sự & Hành chính", "Trưởng phòng Nhân sự"),
    ("Phòng Nhân sự & Hành chính", "Chuyên viên Tuyển dụng & Đào tạo"),
    ("Phòng Nhân sự & Hành chính", "Chuyên viên Tiền lương & Phúc lợi (C&B)"),
    ("Phòng Nhân sự & Hành chính", "Chuyên viên Hành chính - Lễ tân"),

    # Phòng Vận hành & CSKH (7 người)
    ("Phòng Vận hành & CSKH", "Trưởng phòng Vận hành"),
    ("Phòng Vận hành & CSKH", "Trưởng nhóm Hỗ trợ Khách hàng"),
    ("Phòng Vận hành & CSKH", "Chuyên viên Hỗ trợ Kỹ thuật Cấp 1"),
    ("Phòng Vận hành & CSKH", "Chuyên viên Hỗ trợ Kỹ thuật Cấp 2"),
    ("Phòng Vận hành & CSKH", "Điều phối viên Dịch vụ Khách hàng"),
    ("Phòng Vận hành & CSKH", "Chuyên viên Vận hành Hệ thống"),
    ("Phòng Vận hành & CSKH", "Nhân viên Chăm sóc Khách hàng"),
]


def remove_accents(input_str: str) -> str:
    """Chuyển chuỗi tiếng Việt có dấu thành không dấu (ví dụ: Nguyễn Văn An -> nguyen van an)."""
    nfkd_form = unicodedata.normalize("NFKD", input_str)
    no_accent = "".join([c for c in nfkd_form if not unicodedata.combining(c)])
    no_accent = no_accent.replace("đ", "d").replace("Đ", "D")
    return re.sub(r"[^a-zA-Z0-9\s]", "", no_accent).strip().lower()


def generate_email(full_name: str, user_code: str) -> str:
    """Sinh email công vụ chuẩn không dấu từ họ tên hoặc mã nhân viên."""
    clean = remove_accents(full_name)
    parts = clean.split()
    if len(parts) >= 2:
        # Ví dụ: Nguyễn Văn An -> an.nv@faceaccess.vn
        first_name = parts[-1]
        initials = "".join([p[0] for p in parts[:-1]])
        base = f"{first_name}.{initials}"
    else:
        base = f"user.{clean}"
    return f"{base}.{user_code.lower()}@faceaccess.vn"


def generate_phone() -> str:
    """Sinh số điện thoại di động Việt Nam 10 chữ số ngẫu nhiên."""
    prefix = random.choice(PHONE_PREFIXES)
    suffix = "".join([str(random.randint(0, 9)) for _ in range(7)])
    return f"{prefix}{suffix}"


def generate_vietnamese_name() -> str:
    """Sinh họ tên tiếng Việt 3 hoặc 4 chữ tự nhiên."""
    ho = random.choice(HO_LIST)
    is_female = random.choice([True, False])
    if is_female:
        dem = random.choice(DEM_NU)
        ten = random.choice(TEN_NU)
    else:
        dem = random.choice(DEM_NAM)
        ten = random.choice(TEN_NAM)
    return f"{ho} {dem} {ten}"


def build_user_list(count: int = 50, inactive_count: int = 10) -> List[Dict[str, Any]]:
    """Tạo danh sách 50 người dùng ngẫu nhiên với đúng 10 inactive và 40 active."""
    # Lấy đúng số lượng vị trí trong công ty
    slots = list(COMPANY_STRUCTURE[:count])

    # Danh sách trạng thái: 10 inactive (không áp vào CEO/CTO), 40 active
    # Chọn ngẫu nhiên 10 vị trí từ index 3 trở đi để gán inactive
    eligible_inactive_indices = list(range(3, count))
    inactive_indices = set(random.sample(eligible_inactive_indices, inactive_count))

    users = []
    used_names = set()
    used_phones = set()

    for idx, (department, role) in enumerate(slots):
        user_code = f"NV{idx + 1:03d}"

        # Đảm bảo tên không trùng
        for _ in range(30):
            full_name = generate_vietnamese_name()
            if full_name not in used_names:
                break
        used_names.add(full_name)

        # Số điện thoại không trùng
        for _ in range(30):
            phone = generate_phone()
            if phone not in used_phones:
                break
        used_phones.add(phone)

        email = generate_email(full_name, user_code)
        status = "inactive" if idx in inactive_indices else "active"

        users.append({
            "user_code": user_code,
            "full_name": full_name,
            "email": email,
            "phone": phone,
            "department": department,
            "role": role,
            "status": status,
        })

    return users


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Script sinh danh sách 50 người dùng ngẫu nhiên chuẩn Việt Nam và nạp vào Database."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Chỉ in ra danh sách 50 người dùng xem trước, không lưu vào cơ sở dữ liệu."
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Xóa tất cả người dùng hiện tại trước khi tạo mới."
    )
    args = parser.parse_args()

    # Sinh danh sách 50 người dùng
    users = build_user_list(count=50, inactive_count=10)

    print("=" * 80)
    print(f" DANH SÁCH 50 NGƯỜI DÙNG NGẪU NHIÊN (40 ACTIVE, 10 INACTIVE)")
    print("=" * 80)
    print(f"{'Mã NV':<8} | {'Họ và Tên':<22} | {'Trạng thái':<10} | {'Phòng ban':<28} | {'Chức danh'}")
    print("-" * 80)

    for u in users:
        status_display = "[ACTIVE]" if u["status"] == "active" else "[INACTIVE]"
        print(f"{u['user_code']:<8} | {u['full_name']:<22} | {status_display:<10} | {u['department']:<28} | {u['role']}")

    if args.dry_run:
        print("\n[DRY-RUN] Chế độ xem trước: Không có dữ liệu nào được ghi vào Database.")
        return 0

    # Nạp vào Database Supabase
    try:
        settings = load_settings(require_api_key=False)
        db = Database(settings)
    except ConfigurationError as error:
        print(f"\n[CONFIG ERROR] {error}", file=sys.stderr)
        return 1
    except Exception as error:
        print(f"\n[ERROR] Không thể kết nối cơ sở dữ liệu: {error}", file=sys.stderr)
        return 1

    try:
        if args.clear:
            print("\n[CLEAR] Đang xóa dữ liệu người dùng cũ...")
            db.client.table("users").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
            print("[CLEAR] Đã xóa người dùng cũ.")

        print(f"\n[DATABASE] Bắt đầu nạp 50 người dùng vào Supabase (public.users)...")
        # Chia batch chèn an toàn
        batch_size = 25
        inserted_count = 0
        for i in range(0, len(users), batch_size):
            batch = users[i:i + batch_size]
            result = db.client.table("users").insert(batch).execute()
            inserted_count += len(result.data or [])

        print(f"[THÀNH CÔNG] Đã nạp thành công {inserted_count} người dùng vào Database!")
        print(f"             - 40 người dùng: active")
        print(f"             - 10 người dùng: inactive")
        return 0
    except AppError as error:
        print(f"\n[DATABASE ERROR] {error}", file=sys.stderr)
        return 1
    except Exception as error:
        print(f"\n[ERROR] Lỗi khi nạp dữ liệu: {error}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
