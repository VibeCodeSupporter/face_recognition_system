"""Background synchronization and WebSocket trigger listener for Attendance Device."""

from __future__ import annotations

import asyncio
import json
import logging
import threading
from typing import Any
from uuid import uuid4

from PyQt6.QtCore import QObject, QThread, pyqtSignal

from config import settings
from sync.api_client import ApiClient

logger = logging.getLogger(__name__)


class DeviceWebSocketWorker(QThread):
    new_session_received = pyqtSignal(dict)
    session_status_changed = pyqtSignal(dict)
    connection_status = pyqtSignal(bool)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._running = True
        self.device_id = settings.DEVICE_ID or "default_device"
        self.ws_url = f"{settings.BACKEND_WS_URL}/api/v1/ws/devices/{self.device_id}"

    def run(self) -> None:
        asyncio.run(self._ws_loop())

    async def _ws_loop(self) -> None:
        import websockets

        while self._running:
            try:
                logger.info(f"[WS Worker] Connecting to {self.ws_url}...")
                async with websockets.connect(self.ws_url, ping_interval=20, ping_timeout=20) as ws:
                    self.connection_status.emit(True)
                    logger.info("[WS Worker] Connected to Backend WebSocket successfully.")
                    while self._running:
                        try:
                            msg = await asyncio.wait_for(ws.recv(), timeout=30.0)
                            data = json.loads(msg)
                            event = data.get("event")
                            if event == "NEW_REGISTRATION_SESSION":
                                logger.info(f"[WS Worker] Trigger received: {event}")
                                session = data.get("session", {})
                                self.new_session_received.emit(session)
                            elif event in {"SESSION_FINALIZED", "SESSION_CANCELLED"}:
                                session = data.get("session", {})
                                self.session_status_changed.emit(session)
                        except asyncio.TimeoutError:
                            # Send Ping
                            await ws.send(json.dumps({"event": "PING"}))
            except Exception as e:
                self.connection_status.emit(False)
                logger.warning(f"[WS Worker] WebSocket connection failed/disconnected: {e}. Reconnecting in 5s...")
                await asyncio.sleep(5)

    def stop(self) -> None:
        self._running = False
        self.wait(2000)


class DeviceSyncService(QObject):
    new_session_triggered = pyqtSignal(dict)
    connection_changed = pyqtSignal(bool)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.api_client = ApiClient()
        self.ws_worker = DeviceWebSocketWorker(self)
        self.ws_worker.new_session_received.connect(self._on_new_session)
        self.ws_worker.connection_status.connect(self.connection_changed)

    def start(self) -> None:
        if not self.ws_worker.isRunning():
            self.ws_worker.start()

    def stop(self) -> None:
        if self.ws_worker.isRunning():
            self.ws_worker.stop()

    def _on_new_session(self, session: dict) -> None:
        # Enrich user details if needed
        user_id = session.get("user_id")
        if user_id and ("user_code" not in session or not session.get("user_code")):
            user = self.api_client.get_user(user_id)
            if user:
                session["user_code"] = user.get("user_code", "")
                session["full_name"] = user.get("full_name", "")
        self.new_session_triggered.emit(session)

    def send_access_log_async(
        self,
        user_id: str | None,
        result: str,
        confidence: float | None = None,
        access_time: str | None = None,
    ) -> None:
        """Fire and forget access log upload in a background thread."""
        threading.Thread(
            target=self.api_client.send_access_log,
            args=(user_id, result, confidence, access_time),
            daemon=True,
        ).start()

