"""HTTP Client for communicating with FaceAccess Cloud Backend."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import httpx

from config import settings

logger = logging.getLogger(__name__)


class ApiClient:
    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        device_id: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        self.base_url = (base_url or settings.BACKEND_URL).rstrip("/")
        self.api_key = api_key if api_key is not None else settings.BACKEND_API_KEY
        self.device_id = device_id if device_id is not None else settings.DEVICE_ID
        self.timeout = timeout

    @property
    def headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["x-api-key"] = self.api_key
        return headers

    def get_user(self, user_id: str) -> dict[str, Any] | None:
        url = f"{self.base_url}/api/v1/users/{user_id}"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.get(url, headers=self.headers)
                if res.status_code == 200:
                    return res.json().get("data")
        except Exception as e:
            logger.error(f"[ApiClient] get_user failed for {user_id}: {e}")
        return None

    def get_pending_sessions(self) -> list[dict[str, Any]]:
        url = f"{self.base_url}/api/v1/registration-sessions"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                # Lấy toàn bộ các phiên đang chờ đăng ký
                res = client.get(url, headers=self.headers, params={"status": "pending", "limit": 50})
                items = []
                if res.status_code == 200:
                    data = res.json().get("data", {})
                    items = data.get("items", [])

                # Sắp xếp ưu tiên các phiên thuộc đúng device này lên đầu
                if self.device_id:
                    items.sort(key=lambda s: 0 if str(s.get("device_id")) == str(self.device_id) else 1)

                for item in items:
                    if "user_code" not in item and "user_id" in item:
                        user = self.get_user(item["user_id"])
                        if user:
                            item["user_code"] = user.get("user_code", "")
                            item["full_name"] = user.get("full_name", "")
                return items
        except Exception as e:
            logger.error(f"[ApiClient] get_pending_sessions failed: {e}")
        return []

    def upload_face_embedding(
        self,
        user_id: str,
        vector: list[float],
        model_name: str = "GhostFaceNet",
        version: str = "1.3",
    ) -> bool:
        url = f"{self.base_url}/api/v1/users/{user_id}/face-embedding"
        payload = {
            "model_name": model_name,
            "model_version": version,
            "dimension": len(vector),
            "embedding_data": [float(x) for x in vector],
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.put(url, headers=self.headers, json=payload)
                if res.status_code in {200, 201}:
                    logger.info(f"[ApiClient] Uploaded face embedding for user {user_id}")
                    return True
                logger.error(f"[ApiClient] Failed upload embedding: HTTP {res.status_code} - {res.text}")
        except Exception as e:
            logger.error(f"[ApiClient] upload_face_embedding exception: {e}")
        return False

    def has_face_embedding(self, user_id: str) -> bool | None:
        """Check whether the user currently has a face embedding on Cloud Backend.
        Returns True if exists, False if 404 (not registered), or None if offline/error.
        """
        url = f"{self.base_url}/api/v1/users/{user_id}/face-embedding"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.get(url, headers=self.headers)
                if res.status_code == 200:
                    return True
                if res.status_code == 404:
                    return False
                logger.warning(f"[ApiClient] has_face_embedding unexpected HTTP {res.status_code}")
        except Exception as e:
            logger.warning(f"[ApiClient] has_face_embedding offline/error for {user_id}: {e}")
        return None

    def complete_session(self, session_id: str) -> bool:
        url = f"{self.base_url}/api/v1/registration-sessions/{session_id}"
        payload = {"status": "completed"}
        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.patch(url, headers=self.headers, json=payload)
                if res.status_code in {200, 404}:
                    logger.info(f"[ApiClient] Completed/removed session {session_id} (HTTP {res.status_code})")
                    return True
                logger.error(f"[ApiClient] Failed complete session: HTTP {res.status_code} - {res.text}")
        except Exception as e:
            logger.error(f"[ApiClient] complete_session exception: {e}")
        return False

    def resolve_user_id(self, user_code_or_id: str | None) -> str | None:
        """Resolve employee user_code (e.g. NV002) to Supabase user UUID."""
        if not user_code_or_id:
            return None
        # If already a valid UUID
        try:
            return str(uuid4().fromhex(user_code_or_id.replace("-", "")))
        except (ValueError, TypeError, AttributeError):
            pass

        # Check local cache
        if not hasattr(self, "_user_code_map"):
            self._user_code_map: dict[str, str] = {}
        if user_code_or_id in self._user_code_map:
            return self._user_code_map[user_code_or_id]

        # Query backend users list
        try:
            url = f"{self.base_url}/api/v1/users"
            with httpx.Client(timeout=self.timeout) as client:
                res = client.get(url, headers=self.headers)
                if res.status_code == 200:
                    for u in res.json().get("data", []):
                        if u.get("user_code"):
                            self._user_code_map[u["user_code"]] = u["id"]
                    return self._user_code_map.get(user_code_or_id, user_code_or_id)
        except Exception as e:
            logger.warning(f"[ApiClient] resolve_user_id failed for {user_code_or_id}: {e}")
        return user_code_or_id

    def send_access_log(
        self,
        user_id: str | None,
        result: str,
        confidence: float | None = None,
        access_time: str | None = None,
        log_id: str | None = None,
    ) -> bool:
        url = f"{self.base_url}/api/v1/access-logs"
        now = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        resolved_user_id = self.resolve_user_id(user_id) if user_id else None
        payload = {
            "id": log_id or str(uuid4()),
            "user_id": resolved_user_id,
            "device_id": self.device_id or str(uuid4()),
            "result": result,
            "confidence": round(float(confidence), 1) if confidence is not None else None,
            "access_time": access_time or now,
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.post(url, headers=self.headers, json=payload)
                if res.status_code in {200, 201}:
                    logger.info(f"[ApiClient] Log sent: {result} for user {user_id}")
                    return True
                logger.warning(f"[ApiClient] Log failed: HTTP {res.status_code} - {res.text}")
        except Exception as e:
            logger.error(f"[ApiClient] send_access_log exception: {e}")
        return False

