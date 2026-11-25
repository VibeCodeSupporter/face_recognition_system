import hashlib
import secrets
import struct
from datetime import datetime, timezone
from warnings import filters

from app.errors import AppError
from app.repositories import Repositories, TableRepository


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def float32(value: float | None):
    return None if value is None else struct.unpack("!f", struct.pack("!f", value))[0]


class CRUDService:
    def __init__(self, repository: TableRepository):
        self.repository = repository

    def list(self, options: dict):
        return self.repository.list(options)
    
    def list_all(self, filters: dict):
        return self.repository.list_all(filters)
    
    def get(self, record_id: str):
        return self.repository.get(record_id)

    def create(self, values: dict):
        return self.repository.insert(values)

    def update(self, record_id: str, values: dict):
        return self.repository.update(record_id, values)

    def remove(self, record_id: str):
        self.repository.remove(record_id)


class DeviceService(CRUDService):
    def create(self, values: dict):
        token = secrets.token_hex(32)
        record = self.repository.insert({**values, "api_key_hash": hashlib.sha256(token.encode()).hexdigest()})
        return {**record, "device_token": token}


class DeletionHistoryService:
    MAX_ITEMS = 2000

    def __init__(self, history_file=None):
        import threading
        from app.config import BACKEND_ROOT
        self.history_file = history_file or (BACKEND_ROOT / "data" / "deletion_history.json")
        self._lock = threading.Lock()
        self._ensure_dir()

    def _ensure_dir(self):
        try:
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    def _load(self) -> list[dict]:
        import json
        if not self.history_file.is_file():
            return []
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception:
            return []

    def _save(self, items: list[dict]) -> None:
        import json
        self._ensure_dir()
        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(items[:self.MAX_ITEMS], f, ensure_ascii=False, indent=2)

    def record(
        self,
        *,
        entity_type: str,
        entity_id: str,
        title: str,
        reason: str,
        deleted_by: str,
        snapshot: dict,
    ) -> dict:
        from uuid import uuid4
        entry = {
            "id": str(uuid4()),
            "entity_type": entity_type,
            "entity_id": str(entity_id),
            "title": title,
            "reason": reason,
            "deleted_by": deleted_by,
            "deleted_at": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "snapshot": snapshot,
        }
        with self._lock:
            items = self._load()
            items.insert(0, entry)
            self._save(items)
        return entry

    def list(self, options: dict) -> dict:
        with self._lock:
            items = self._load()

        entity_type = options.get("entity_type")
        search = (options.get("search") or "").strip().lower()
        start_time = parse_time(options["start_time"]) if options.get("start_time") else None
        end_time = parse_time(options["end_time"]) if options.get("end_time") else None

        filtered = []
        for item in items:
            if entity_type and item.get("entity_type") != entity_type:
                continue
            if search:
                haystack = " ".join([
                    str(item.get("title", "")),
                    str(item.get("entity_id", "")),
                    str(item.get("reason", "")),
                    str(item.get("deleted_by", "")),
                ]).lower()
                if search not in haystack:
                    continue
            item_time = parse_time(item["deleted_at"]) if item.get("deleted_at") else None
            if start_time is not None and (item_time is None or item_time < start_time):
                continue
            if end_time is not None and (item_time is None or item_time > end_time):
                continue
            filtered.append(item)

        limit = options.get("limit", 20)
        offset = options.get("offset", 0)
        page = filtered[offset:offset + limit]
        return {
            "items": page,
            "total": len(filtered),
            "limit": limit,
            "offset": offset,
            "has_more": len(filtered) > offset + limit,
        }

    def clear(self) -> dict:
        with self._lock:
            items = self._load()
            count = len(items)
            self._save([])
        return {"cleared_count": count}


class EmbeddingService:
    def __init__(self, repositories: Repositories, deletion_history: DeletionHistoryService | None = None):
        self.repositories = repositories
        self.deletion_history = deletion_history

    def get(self, user_id: str):
        return self.repositories.embeddings.get(user_id)

    def save(self, user_id: str, values: dict):
        saved, _ = self.save_and_finalize(user_id, values)
        return saved

    def save_and_finalize(self, user_id: str, values: dict, deleted_by: str = "Hệ thống / Thiết bị (API Key)") -> tuple[dict, list[dict]]:
        user = self.repositories.users.get(user_id)
        saved = self.repositories.embeddings.upsert({"image_url": None, **values, "user_id": user_id})

        # Tự động hoàn tất và xóa các phiên đang chờ (pending) của người dùng này
        pending_sessions = self.repositories.sessions.list_all({"user_id": user_id, "status": "pending"})
        finalized = []
        now = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        for sess in pending_sessions:
            completed_snapshot = {**sess, "status": "completed", "completed_at": now}
            self.repositories.sessions.remove(sess["id"])
            if self.deletion_history is not None:
                self.deletion_history.record(
                    entity_type="session",
                    entity_id=sess["id"],
                    title=f"[{user.get('user_code', '')}] {user.get('full_name', user_id)}".strip(),
                    reason="Hoàn tất đăng ký khuôn mặt (tự động xóa sau khi có embedding)",
                    deleted_by=deleted_by,
                    snapshot=completed_snapshot,
                )
            finalized.append(completed_snapshot)

        return saved, finalized

    def remove(self, user_id: str):
        self.repositories.embeddings.remove(user_id)


class SessionService(CRUDService):
    def __init__(self, repositories: Repositories):
        super().__init__(repositories.sessions)
        self.repositories = repositories

    def create(self, values: dict):
        user = self.repositories.users.get(values["user_id"])
        if user["status"] != "active":
            raise AppError(409, "USER_INACTIVE", "An inactive user cannot start enrollment.")

        # 1. Chặn tạo phiên nếu người dùng đã có face embedding trong hệ thống
        try:
            self.repositories.embeddings.get(values["user_id"])
            raise AppError(
                409,
                "USER_ALREADY_REGISTERED",
                "Người dùng này đã có dữ liệu khuôn mặt trong hệ thống. Không thể tạo phiên đăng ký mới.",
            )
        except AppError as e:
            if e.code != "NOT_FOUND":
                raise

        # 2. Chặn tạo phiên trùng lặp nếu người dùng đang có một phiên pending khác
        user_pending = self.repository.list({"user_id": values["user_id"], "status": "pending", "limit": 1, "offset": 0})
        if user_pending.get("items"):
            raise AppError(
                409,
                "USER_HAS_PENDING_SESSION",
                "Người dùng này hiện đã có một phiên đăng ký đang chờ xử lý.",
            )

        self.repositories.devices.get(values["device_id"])
        pending = self.repository.list({"device_id": values["device_id"], "status": "pending", "limit": 10, "offset": 0})
        if len(pending.get("items", [])) >= 10:
            raise AppError(429, "DEVICE_QUEUE_FULL", "Thiết bị hiện đã có 10 phiên đang chờ xử lý. Vui lòng đợi thiết bị hoàn tất các phiên trước.")
        return self.repository.insert(values)

    def update(self, record_id: str, values: dict):
        session = self.repository.get(record_id)
        if session["status"] != "pending" or parse_time(session["expires_at"]) <= datetime.now(timezone.utc):
            raise AppError(409, "SESSION_NOT_PENDING", "The session is expired or has already been finalized.")
        status = values["status"]
        if status == "completed":
            try:
                self.repositories.embeddings.get(session["user_id"])
            except AppError as error:
                if error.code == "NOT_FOUND":
                    raise AppError(409, "FACE_REQUIRED", "Save a face embedding before completing enrollment.") from None
                raise
        now = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        return self.repository.finalize(record_id, {"status": status, "completed_at": now if status == "completed" else None}, now)


class AccessLogService:
    def __init__(self, repository: TableRepository, users_repo: TableRepository | None = None):
        self.repository = repository
        self.users_repo = users_repo

    def list(self, options: dict):
        return self.repository.list(options)

    def get(self, record_id: str):
        return self.repository.get(record_id)

    def create(self, values: dict) -> tuple[dict, bool]:
        record = {"user_id": None, "confidence": None, **values}
        uid = record.get("user_id")
        if uid is not None:
            from uuid import UUID
            try:
                UUID(str(uid))
            except (ValueError, TypeError):
                # Identifier is not a UUID, resolve from user_code
                if self.users_repo is not None:
                    users = self.users_repo.list_all({"user_code": str(uid)})
                    if users:
                        record["user_id"] = users[0]["id"]
                    else:
                        raise AppError(404, "USER_NOT_FOUND", f"User code '{uid}' not found.")
                else:
                    raise AppError(400, "INVALID_USER_ID", f"Invalid user ID format: '{uid}'")
        try:
            return self.repository.insert(record), True
        except AppError as error:
            if error.code != "DUPLICATE":
                raise
        existing = self.repository.get(record["id"])
        identical = all(existing[field] == record[field] for field in ("user_id", "device_id", "result"))
        identical = identical and float32(existing["confidence"]) == float32(record["confidence"])
        identical = identical and parse_time(existing["access_time"]) == parse_time(record["access_time"])
        if not identical:
            raise AppError(409, "LOG_ID_CONFLICT", "This log ID already belongs to a different event.")
        return existing, False

    def delete_by_range(self, options: dict, deleted_by: str = "Quản trị viên") -> dict:
        deleted_rows = self.repository.delete_range(options)
        deleted_count = len(deleted_rows)
        return {
            "deleted_count": deleted_count,
            "deleted_rows": deleted_rows,
            "start_time": options["start_time"],
            "end_time": options["end_time"],
        }



class AuthService:
    def __init__(self, settings=None):
        from app.config import BACKEND_ROOT
        self.settings = settings
        self.admin_file = BACKEND_ROOT / "data" / "admins.json"
        self._ensure_admin_dir()

    def _ensure_admin_dir(self):
        try:
            self.admin_file.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    def _get_admins(self) -> dict:
        from app.rbac import ROLE_ADMIN, ROLE_OPERATOR

        admins = {
            "operator": {
                "password": "operator123",
                "full_name": "Nhân viên Vận hành",
                "role": ROLE_OPERATOR,
            }
        }
        if self.settings and self.settings.admin_username and self.settings.admin_password:
            admins[self.settings.admin_username] = {
                "password": self.settings.admin_password,
                "full_name": "Quản trị viên Hệ thống",
                "role": ROLE_ADMIN,
            }
        else:
            admins["admin"] = {
                "password": "admin123",
                "full_name": "Quản trị viên Hệ thống",
                "role": ROLE_ADMIN,
            }
        if self.admin_file.is_file():
            try:
                import json
                with open(self.admin_file, "r", encoding="utf-8") as f:
                    stored = json.load(f)
                    if isinstance(stored, dict):
                        admins.update(stored)
            except Exception:
                pass
        return admins

    def _get_secret(self) -> str:
        if self.settings:
            return self.settings.jwt_secret or self.settings.api_key or "default_jwt_secret_key_32_chars_long"
        return "default_jwt_secret_key_32_chars_long"

    def login(self, username: str, password: str) -> dict:
        import hmac
        import time
        import jwt
        from app.rbac import ROLE_ADMIN, get_permissions_for_role

        admins = self._get_admins()
        user_data = admins.get(username)
        if not user_data:
            raise AppError(401, "INVALID_CREDENTIALS", "Tên đăng nhập hoặc mật khẩu không chính xác.")

        expected_pw = user_data["password"]
        if not hmac.compare_digest(password, expected_pw):
            raise AppError(401, "INVALID_CREDENTIALS", "Tên đăng nhập hoặc mật khẩu không chính xác.")

        role = user_data.get("role", ROLE_ADMIN)
        permissions = get_permissions_for_role(role)
        now = int(time.time())
        exp = now + 86400 * 7
        secret = self._get_secret()
        payload = {
            "sub": username,
            "role": role,
            "full_name": user_data.get("full_name", "Quản trị viên"),
            "iat": now,
            "exp": exp,
        }
        token = jwt.encode(payload, secret, algorithm="HS256")
        return {
            "token": token,
            "admin": {
                "username": username,
                "full_name": user_data.get("full_name", "Quản trị viên"),
                "role": role,
                "permissions": permissions,
            },
        }

    def verify_token(self, token: str) -> dict:
        import jwt
        secret = self._get_secret()
        try:
            return jwt.decode(token, secret, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            raise AppError(401, "UNAUTHORIZED", "Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.") from None
        except Exception:
            raise AppError(401, "UNAUTHORIZED", "Token xác thực không hợp lệ.") from None

    def update_profile(self, username: str, full_name: str | None = None, new_password: str | None = None) -> dict:
        import json
        from app.rbac import ROLE_ADMIN, get_permissions_for_role

        admins = self._get_admins()
        current = dict(admins.get(username, {
            "password": "admin123",
            "full_name": "Quản trị viên Hệ thống",
            "role": ROLE_ADMIN,
        }))
        if full_name:
            current["full_name"] = full_name.strip()
        if new_password:
            current["password"] = new_password

        stored = {}
        if self.admin_file.is_file():
            try:
                with open(self.admin_file, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    if isinstance(loaded, dict):
                        stored = loaded
            except Exception:
                pass
        stored[username] = current
        self._ensure_admin_dir()
        with open(self.admin_file, "w", encoding="utf-8") as f:
            json.dump(stored, f, ensure_ascii=False, indent=2)

        role = current.get("role", ROLE_ADMIN)
        return {
            "username": username,
            "full_name": current["full_name"],
            "role": role,
            "permissions": get_permissions_for_role(role),
        }


class Services:
    def __init__(self, repositories: Repositories, settings=None):
        self.deletion_history = DeletionHistoryService()
        self.users = CRUDService(repositories.users)
        self.devices = DeviceService(repositories.devices)
        self.embeddings = EmbeddingService(repositories, self.deletion_history)
        self.sessions = SessionService(repositories)
        self.logs = AccessLogService(repositories.logs, repositories.users)

        self.auth = AuthService(settings)

