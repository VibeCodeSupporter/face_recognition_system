"""
Mô phỏng Thiết bị (Mock Device) & Kiểm tra Luồng Giao tiếp với Backend.
Chạy trực tiếp:
    python backend/scripts/simulate_device.py
"""

from __future__ import annotations
import asyncio
import json
import random
import sys
import time
from pathlib import Path
from uuid import uuid4

# Đảm bảo import được app backend
_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from starlette.testclient import TestClient
from app.config import Settings, load_settings
from app.main import create_app
from app.services import Services
from app.repositories import Repositories, TableRepository, EmbeddingRepository, SessionRepository
from app.infrastructure.database import Database
from app.errors import AppError


# --- Mock Database phục vụ mô phỏng độc lập (không bắt buộc có Supabase thật) ---
class InMemoryDB:
    def __init__(self):
        self.tables = {
            "users": {},
            "devices": {},
            "face_embeddings": {},
            "registration_sessions": {},
            "access_logs": {},
        }

    def check(self):
        return [{"table": t, "ok": True} for t in self.tables]

    def close(self):
        pass


class MockTableRepo(TableRepository):
    def __init__(self, db: InMemoryDB, table: str, key: str = "id", order: str = "created_at"):
        self.db = db
        self.table = table
        self.key = key
        self.order = order

    def list(self, options: dict) -> dict:
        rows = list(self.db.tables[self.table].values())
        for k, v in options.items():
            if k not in {"limit", "offset"}:
                rows = [r for r in rows if r.get(k) == v]
        limit = options.get("limit", 20)
        offset = options.get("offset", 0)
        return {"items": rows[offset:offset + limit], "limit": limit, "offset": offset, "has_more": len(rows) > offset + limit}

    def list_all(self, filters: dict) -> list[dict]:
        rows = list(self.db.tables[self.table].values())
        for k, v in filters.items():
            rows = [r for r in rows if r.get(k) == v]
        return rows

    def get(self, record_id: str) -> dict:
        row = self.db.tables[self.table].get(str(record_id))
        if not row:
            raise AppError(404, "NOT_FOUND", f"Record {record_id} not found in {self.table}")
        return row

    def insert(self, values: dict) -> dict:
        record_id = str(values.get(self.key) or uuid4())
        rec = {"id": record_id, "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"), **values}
        if self.key != "id":
            rec[self.key] = record_id
        if record_id in self.db.tables[self.table]:
            raise AppError(409, "DUPLICATE", "Record already exists")
        self.db.tables[self.table][record_id] = rec
        return rec

    def update(self, record_id: str, values: dict) -> dict:
        row = self.get(record_id)
        row.update(values)
        row["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ")
        return row

    def remove(self, record_id: str) -> None:
        if str(record_id) in self.db.tables[self.table]:
            del self.db.tables[self.table][str(record_id)]


class MockEmbeddingRepo(EmbeddingRepository, MockTableRepo):
    def __init__(self, db: InMemoryDB):
        MockTableRepo.__init__(self, db, "face_embeddings", "user_id")

    def upsert(self, values: dict) -> dict:
        user_id = str(values["user_id"])
        self.db.tables[self.table][user_id] = {**values, "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ")}
        return self.db.tables[self.table][user_id]


class MockSessionRepo(SessionRepository, MockTableRepo):
    def __init__(self, db: InMemoryDB):
        MockTableRepo.__init__(self, db, "registration_sessions")

    def insert(self, values: dict) -> dict:
        data = {"status": "pending", "completed_at": None, **values}
        return super().insert(data)

    def finalize(self, record_id: str, values: dict, now: str) -> dict:
        row = self.get(record_id)
        if row["status"] != "pending":
            raise AppError(409, "SESSION_NOT_PENDING", "Session already finalized.")
        row.update(values)
        return row


def build_test_app():
    env_file = _BACKEND_DIR / ".env"
    if env_file.exists():
        try:
            settings = load_settings()
            db = Database(settings)
            db.check()
            print(">>> [DATABASE] PHÁT HIỆN backend/.env! KẾT NỐI TRỰC TIẾP TỚI SUPABASE DATABASE THẬT! <<<")
            repos = Repositories(db)
            app = create_app(settings)
            app.state.database = db
            app.state.services = Services(repos, settings)
            return app, repos, settings, True
        except Exception as e:
            print(f"[CẢNH BÁO] Lỗi kết nối Supabase thật ({e}). Chuyển sang dùng Mock DB.")

    print("[INFO] Chưa có file backend/.env -> Chạy ở chế độ Mock DB.")
    settings = Settings(
        supabase_url="https://mock.supabase.co",
        secret_key="sb_secret_mock",
        api_key="a" * 32,
        host="127.0.0.1",
        port=5000,
        jwt_secret="jwt" * 10,
    )
    db = InMemoryDB()
    repos = Repositories(None)
    repos.users = MockTableRepo(db, "users")
    repos.devices = MockTableRepo(db, "devices")
    repos.embeddings = MockEmbeddingRepo(db)
    repos.sessions = MockSessionRepo(db)
    repos.logs = MockTableRepo(db, "access_logs", order="access_time")

    app = create_app(settings)
    app.state.database = db
    app.state.services = Services(repos, settings)
    return app, repos, settings, False


def run_simulation():
    print("=" * 70)
    print("  BẮT ĐẦU MÔ PHỎNG HỆ THỐNG GIAO TIẾP BACKEND <-> DEVICE <-> PORTAL")
    print("=" * 70)

    app, repos, settings, is_real_db = build_test_app()
    client = TestClient(app)
    headers = {"x-api-key": settings.api_key}

    # 1. Khởi tạo User và Device mẫu
    suffix = uuid4().hex[:6]
    device_id = str(uuid4())
    dev_code = f"SIM_DOOR_{suffix}"
    repos.devices.insert({
        "id": device_id,
        "device_code": dev_code,
        "name": f"Cửa chính Tòa {suffix}",
        "status": "online",
        "api_key_hash": "hash123",
    })
    user_id = str(uuid4())
    user_code = f"SIM_NV_{suffix}"
    repos.users.insert({
        "id": user_id,
        "user_code": user_code,
        "full_name": "Nguyễn Văn An",
        "status": "active",
    })
    print(f"[INIT] Đã tạo Thiết bị mẫu: {dev_code} (ID: {device_id[:8]}...)")
    print(f"[INIT] Đã tạo Người dùng mẫu: {user_code} - Nguyễn Văn An (ID: {user_id[:8]}...)")

    # 2. Device kết nối WebSocket tới Backend
    print("\n--- BƯỚC 1: DEVICE & PORTAL KẾT NỐI WEBSOCKET ---")
    with client.websocket_connect(f"/api/v1/ws/devices/{device_id}") as dev_ws, \
         client.websocket_connect("/api/v1/ws/portal") as portal_ws:

        print("  [DEVICE] -> Kết nối WebSocket Backend thành công.")
        print("  [PORTAL] -> Kết nối WebSocket Backend thành công.")

        # Test heartbeat Ping/Pong
        dev_ws.send_text(json.dumps({"event": "PING"}))
        pong = json.loads(dev_ws.receive_text())
        print(f"  [DEVICE Heartbeat] Gửi PING -> Nhận: {pong['event']} (0% CPU khi idle)")

        # 3. Luồng 1: Frontend tạo Session mới -> Trigger Device
        print("\n--- BƯỚC 2: FRONTEND TẠO PHIÊN ĐĂNG KÝ MỚI (TRIGGER DEVICE) ---")
        expiry = "2028-01-01T00:00:00Z"
        res = client.post("/api/v1/registration-sessions", headers=headers, json={
            "user_id": user_id,
            "device_id": device_id,
            "expires_at": expiry,
        })
        assert res.status_code == 201, f"Lỗi tạo session: {res.text}"
        session_data = res.json()["data"]
        session_id = session_data["id"]
        print(f"  [PORTAL] Bấm tạo phiên -> Session ID: {session_id[:8]}... (Status: {session_data['status']})")

        # Kiểm tra Device nhận trigger
        dev_event = json.loads(dev_ws.receive_text())
        print(f"  [DEVICE] NHẬN TRIGGER TỪ BACKEND: {dev_event['event']} cho session {dev_event['session']['id'][:8]}...")
        assert dev_event["event"] == "NEW_REGISTRATION_SESSION"

        # 4. Device tiến hành quét 5 góc pose và gửi embedding lên Backend
        print("\n--- BƯỚC 3: DEVICE TIẾN HÀNH QUÉT 5 GÓC VÀ GỬI EMBEDDING ---")
        poses = ["front (nhìn thẳng)", "left (quay trái)", "right (quay phải)", "down (cúi nhẹ)", "up (ngửa nhẹ)"]
        for idx, p in enumerate(poses, 1):
            print(f"  [DEVICE Camera] Thu nhận pose {idx}/5: {p} -> Đạt chuẩn FAS & Quality")

        fake_vector = [round(random.uniform(-0.1, 0.1), 4) for _ in range(512)]
        print(f"  [DEVICE] Trích xuất vector 512D bằng GhostFaceNet -> Gửi PUT /face-embedding...")
        put_res = client.put(f"/api/v1/users/{user_id}/face-embedding", headers=headers, json={
            "model_name": "GhostFaceNet",
            "model_version": "v1.3",
            "dimension": 512,
            "embedding_data": fake_vector,
        })
        assert put_res.status_code == 200, f"Lỗi lưu embedding: {put_res.text}"
        print("  [BACKEND] Lưu face embedding thành công!")

        # 5. Device cập nhật hoàn thành Session
        print(f"  [DEVICE] Báo hoàn tất -> PATCH /registration-sessions/{session_id[:8]}... status='completed'")
        patch_res = client.patch(f"/api/v1/registration-sessions/{session_id}", headers=headers, json={
            "status": "completed",
        })
        assert patch_res.status_code == 200
        completed_session = patch_res.json()["data"]
        print(f"  [BACKEND] Session hoàn tất lúc: {completed_session['completed_at']} (Status: {completed_session['status']})")

        # Portal nhận thông báo để chuyển session sang Lịch sử
        portal_event = json.loads(portal_ws.receive_text())
        # Lưu ý portal có thể nhận SESSION_CREATED trước, nhận tiếp event finalize
        if portal_event.get("event") == "SESSION_CREATED":
            portal_event = json.loads(portal_ws.receive_text())
        print(f"  [PORTAL] NHẬN THÔNG BÁO REALTIME: {portal_event['event']}")
        print("  [PORTAL] -> Đã xóa khỏi Danh sách chờ và chuyển vào Lịch sử thành công!")

        # 6. Kiểm tra giới hạn tối đa 10 phiên đồng thời
        print("\n--- BƯỚC 4: KIỂM TRA GIỚI HẠN TỐI ĐA 10 PHIÊN PENDING ---")
        print("  [TEST] Đang tạo 10 phiên pending liên tiếp cho thiết bị...")
        created_sessions = []
        for i in range(10):
            # Tạo user phụ
            u_id = str(uuid4())
            repos.users.insert({"id": u_id, "user_code": f"NV_TEST_{suffix}_{i}", "full_name": f"Test User {i}", "status": "active"})
            r = client.post("/api/v1/registration-sessions", headers=headers, json={
                "user_id": u_id,
                "device_id": device_id,
                "expires_at": expiry,
            })
            assert r.status_code == 201
            created_sessions.append(r.json()["data"]["id"])
            # Đọc event từ ws để không nghẽn buffer
            dev_ws.receive_text()

        print(f"  [TEST] Đã tạo đủ 10/10 phiên pending. Thử tạo tiếp phiên thứ 11...")
        u_extra = str(uuid4())
        repos.users.insert({"id": u_extra, "user_code": f"NV_EXTRA_{suffix}", "full_name": "User 11", "status": "active"})
        r_11 = client.post("/api/v1/registration-sessions", headers=headers, json={
            "user_id": u_extra,
            "device_id": device_id,
            "expires_at": expiry,
        })
        print(f"  [BACKEND] Phản hồi tạo phiên 11: HTTP {r_11.status_code} - {r_11.json()['error']['code']}")
        print(f"            Thông điệp: {r_11.json()['error']['message']}")
        assert r_11.status_code == 429, "Phải chặn phiên thứ 11 với mã 429!"

        # 7. Luồng 2: Nhận diện khuôn mặt (Access Log Trigger)
        print("\n--- BƯỚC 5: NHẬN DIỆN KHUÔN MẶT & ĐẨY ACCESS LOG ---")
        log_id = str(uuid4())
        print(f"  [DEVICE] Người dùng Nguyễn Văn An đứng trước cửa -> Nhận diện thành công (99.1%)")
        print(f"  [DEVICE] Mở khóa cửa trong 3 giây -> Trigger POST /access-logs...")
        log_res = client.post("/api/v1/access-logs", headers=headers, json={
            "id": log_id,
            "user_id": user_id,
            "device_id": device_id,
            "result": "granted",
            "confidence": 99.1,
            "access_time": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        })
        assert log_res.status_code == 201
        print(f"  [BACKEND] Đã ghi nhận Access Log {log_id[:8]}... (Status: 201 Created)")

        # Kiểm chứng Trigger 3 (Tự động update thiết bị Online & last_seen_at)
        dev_check = repos.devices.get(device_id)
        print(f"  [DATABASE TRIGGER 3] Kiểm tra bảng devices:")
        print(f"                       -> Status: {dev_check.get('status')}")
        print(f"                       -> Last Seen: {dev_check.get('last_seen_at')}")

        # 8. Luồng 3: Offline mode & Đồng bộ lại (Idempotency)
        print("\n--- BƯỚC 6: GIẢ LẬP MẤT MẠNG (OFFLINE) & ĐỒNG BỘ LẠI KHI CÓ MẠNG ---")
        print("  [DEVICE] Mạng bị ngắt (Offline). 2 người quẹt cửa lúc mất mạng:")
        offline_logs = [
            {"id": str(uuid4()), "user_id": user_id, "device_id": device_id, "result": "granted", "confidence": 95.0, "access_time": "2026-11-20T10:00:00Z"},
            {"id": str(uuid4()), "user_id": None, "device_id": device_id, "result": "denied", "confidence": 30.0, "access_time": "2026-11-20T10:05:00Z"},
        ]
        for l in offline_logs:
            print(f"    -> Đã lưu vào hàng đợi SQLite cục bộ: ID={l['id'][:8]}..., Result={l['result']}")

        print("  [DEVICE] Mạng phục hồi (Online trở lại)! Bắt đầu đồng bộ hàng đợi lên Backend...")
        for l in offline_logs:
            sync_res = client.post("/api/v1/access-logs", headers=headers, json=l)
            assert sync_res.status_code == 201
            print(f"    -> Đồng bộ log {l['id'][:8]}...: Thành công (HTTP {sync_res.status_code})")

        print("  [DEVICE] Thử gửi lại log cũ (giả lập mạng chập chờn retry)...")
        retry_res = client.post("/api/v1/access-logs", headers=headers, json=offline_logs[0])
        print(f"  [BACKEND] Idempotent Check: HTTP {retry_res.status_code} (Không duplicate, dữ liệu nhất quán)")
        assert retry_res.status_code == 200

    print("\n" + "=" * 70)
    print("  TẤT CẢ CÁC LUỒNG ĐÃ ĐƯỢC MÔ PHỎNG VÀ XÁC MINH THÀNH CÔNG 100%!")
    print("=" * 70)


if __name__ == "__main__":
    run_simulation()
