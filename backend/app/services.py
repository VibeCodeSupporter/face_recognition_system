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


class EmbeddingService:
    def __init__(self, repositories: Repositories):
        self.repositories = repositories

    def get(self, user_id: str):
        return self.repositories.embeddings.get(user_id)

    def save(self, user_id: str, values: dict):
        self.repositories.users.get(user_id)
        return self.repositories.embeddings.upsert({"image_url": None, **values, "user_id": user_id})

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
        self.repositories.devices.get(values["device_id"])
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
    def __init__(self, repository: TableRepository):
        self.repository = repository

    def list(self, options: dict):
        return self.repository.list(options)

    def get(self, record_id: str):
        return self.repository.get(record_id)

    def create(self, values: dict) -> tuple[dict, bool]:
        record = {"user_id": None, "confidence": None, **values}
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
        admins = {}
        if self.settings:
            admins[self.settings.admin_username] = {
                "password": self.settings.admin_password,
                "full_name": "Quản trị viên Hệ thống",
                "role": "admin",
            }
        else:
            admins["admin"] = {
                "password": "admin123",
                "full_name": "Quản trị viên Hệ thống",
                "role": "admin",
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

        admins = self._get_admins()
        user_data = admins.get(username)
        if not user_data:
            raise AppError(401, "INVALID_CREDENTIALS", "Tên đăng nhập hoặc mật khẩu không chính xác.")

        expected_pw = user_data["password"]
        if not hmac.compare_digest(password, expected_pw):
            raise AppError(401, "INVALID_CREDENTIALS", "Tên đăng nhập hoặc mật khẩu không chính xác.")

        now = int(time.time())
        exp = now + 86400 * 7
        secret = self._get_secret()
        payload = {
            "sub": username,
            "role": user_data.get("role", "admin"),
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
                "role": user_data.get("role", "admin"),
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


class Services:
    def __init__(self, repositories: Repositories, settings=None):
        self.users = CRUDService(repositories.users)
        self.devices = DeviceService(repositories.devices)
        self.embeddings = EmbeddingService(repositories)
        self.sessions = SessionService(repositories)
        self.logs = AccessLogService(repositories.logs)
        self.auth = AuthService(settings)
