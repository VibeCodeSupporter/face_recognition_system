import json
import logging
from typing import Dict, Set
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        # device_id -> set of active WebSockets (allows reconnect / multi-tab)
        self.active_devices: Dict[str, Set[WebSocket]] = {}
        # portal clients (Web dashboard users)
        self.portal_clients: Set[WebSocket] = set()

    async def connect_device(self, device_id: str, websocket: WebSocket):
        await websocket.accept()
        if device_id not in self.active_devices:
            self.active_devices[device_id] = set()
        self.active_devices[device_id].add(websocket)
        logger.info(f"[WS] Device {device_id} connected. Active connections: {len(self.active_devices[device_id])}")

    def disconnect_device(self, device_id: str, websocket: WebSocket):
        if device_id in self.active_devices:
            self.active_devices[device_id].discard(websocket)
            if not self.active_devices[device_id]:
                del self.active_devices[device_id]
        logger.info(f"[WS] Device {device_id} disconnected.")

    async def broadcast_to_devices(self, message: dict):
        """Broadcast live event to all connected edge devices."""
        if not self.active_devices:
            return
        payload = json.dumps(message)
        for device_id, connections in list(self.active_devices.items()):
            dead = set()
            for ws in list(connections):
                try:
                    await ws.send_text(payload)
                except Exception as e:
                    logger.error(f"[WS] Broadcast failed for device {device_id}: {e}")
                    dead.add(ws)
            for d in dead:
                connections.discard(d)

    async def send_to_device(self, device_id: str, message: dict) -> bool:
        """Send message to a specific device. If not connected, fallback to broadcast so active devices receive it."""
        connections = self.active_devices.get(device_id, set())
        if not connections:
            logger.warning(f"[WS] Device {device_id} is not directly connected to WebSocket. Broadcasting...")
            await self.broadcast_to_devices(message)
            return True

        dead_connections = set()
        delivered = False
        payload = json.dumps(message)
        for ws in connections:
            try:
                await ws.send_text(payload)
                delivered = True
            except Exception as e:
                logger.error(f"[WS] Failed sending to device {device_id}: {e}")
                dead_connections.add(ws)

        for dead in dead_connections:
            connections.discard(dead)
        return delivered

    async def connect_portal(self, websocket: WebSocket):
        await websocket.accept()
        self.portal_clients.add(websocket)
        logger.info(f"[WS] Portal client connected. Total portal clients: {len(self.portal_clients)}")

    def disconnect_portal(self, websocket: WebSocket):
        self.portal_clients.discard(websocket)
        logger.info(f"[WS] Portal client disconnected.")

    async def broadcast_to_portal(self, message: dict):
        """Broadcast live event to all connected web portal dashboards."""
        if not self.portal_clients:
            return
        dead_clients = set()
        payload = json.dumps(message)
        for ws in self.portal_clients:
            try:
                await ws.send_text(payload)
            except Exception:
                dead_clients.add(ws)
        for dead in dead_clients:
            self.portal_clients.discard(dead)


# Global instance
manager = ConnectionManager()

