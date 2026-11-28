from __future__ import annotations
import json
import random
import time
from uuid import uuid4
import pytest
from starlette.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.services import Services
from app.repositories import Repositories
from app.errors import AppError
from scripts.simulate_device import (
    InMemoryDB,
    MockTableRepo,
    MockEmbeddingRepo,
    MockSessionRepo,
    MockAccessLogRepo,
)


@pytest.fixture
def sim_context():
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
    repos.logs = MockAccessLogRepo(db)

    app = create_app(settings)
    app.state.database = db
    app.state.services = Services(repos, settings)

    client = TestClient(app)
    headers = {"x-api-key": settings.api_key}

    device_id = str(uuid4())
    repos.devices.insert({
        "id": device_id,
        "device_code": "DOOR_01",
        "name": "Front Door",
        "status": "online",
        "api_key_hash": "hash123",
    })
    user_id = str(uuid4())
    repos.users.insert({
        "id": user_id,
        "user_code": "USER_01",
        "full_name": "Test User",
        "status": "active",
    })
    return {
        "client": client,
        "headers": headers,
        "repos": repos,
        "device_id": device_id,
        "user_id": user_id,
    }


def test_device_websocket_trigger_and_registration(sim_context):
    client = sim_context["client"]
    headers = sim_context["headers"]
    device_id = sim_context["device_id"]
    user_id = sim_context["user_id"]
    expiry = "2028-01-01T00:00:00Z"

    with client.websocket_connect(f"/api/v1/ws/devices/{device_id}") as dev_ws, \
         client.websocket_connect("/api/v1/ws/portal") as portal_ws:

        # 1. Heartbeat check
        dev_ws.send_text(json.dumps({"event": "PING"}))
        pong = json.loads(dev_ws.receive_text())
        assert pong.get("event") == "PONG"

        # 2. Create session triggers device via websocket
        res = client.post("/api/v1/registration-sessions", headers=headers, json={
            "user_id": user_id,
            "device_id": device_id,
            "expires_at": expiry,
        })
        assert res.status_code == 201
        session_id = res.json()["data"]["id"]

        dev_msg = json.loads(dev_ws.receive_text())
        assert dev_msg["event"] == "NEW_REGISTRATION_SESSION"
        assert dev_msg["session"]["id"] == session_id

        # 3. Device sends face embedding -> backend auto-completes & deletes pending session
        vector = [round(random.uniform(-0.1, 0.1), 4) for _ in range(512)]
        put_res = client.put(f"/api/v1/users/{user_id}/face-embedding", headers=headers, json={
            "model_name": "GhostFaceNet",
            "model_version": "v1.3",
            "dimension": 512,
            "embedding_data": vector,
        })
        assert put_res.status_code == 200

        # Session was automatically completed and deleted from active registration_sessions
        assert client.get(f"/api/v1/registration-sessions/{session_id}", headers=headers).status_code == 404

        # Portal receives SESSION_FINALIZED event
        portal_msg = json.loads(portal_ws.receive_text())
        while portal_msg.get("event") == "SESSION_CREATED":
            portal_msg = json.loads(portal_ws.receive_text())
        assert portal_msg["event"] == "SESSION_FINALIZED"
        assert portal_msg["session"]["status"] == "completed"
        assert portal_msg["session"]["id"] == session_id


def test_device_max_ten_pending_sessions_limit(sim_context):
    client = sim_context["client"]
    headers = sim_context["headers"]
    device_id = sim_context["device_id"]
    repos = sim_context["repos"]
    expiry = "2028-01-01T00:00:00Z"

    # Create 10 pending sessions
    for i in range(10):
        u_id = str(uuid4())
        repos.users.insert({"id": u_id, "user_code": f"Q_USER_{i}", "full_name": f"User {i}", "status": "active"})
        r = client.post("/api/v1/registration-sessions", headers=headers, json={
            "user_id": u_id,
            "device_id": device_id,
            "expires_at": expiry,
        })
        assert r.status_code == 201

    # 11th session must be rejected with 429 DEVICE_QUEUE_FULL
    u_extra = str(uuid4())
    repos.users.insert({"id": u_extra, "user_code": "Q_USER_11", "full_name": "User 11", "status": "active"})
    r_11 = client.post("/api/v1/registration-sessions", headers=headers, json={
        "user_id": u_extra,
        "device_id": device_id,
        "expires_at": expiry,
    })
    assert r_11.status_code == 429
    assert r_11.json()["error"]["code"] == "DEVICE_QUEUE_FULL"


def test_device_offline_and_idempotent_sync(sim_context):
    client = sim_context["client"]
    headers = sim_context["headers"]
    device_id = sim_context["device_id"]
    user_id = sim_context["user_id"]

    log_entry = {
        "id": str(uuid4()),
        "user_id": user_id,
        "device_id": device_id,
        "result": "granted",
        "confidence": 97.5,
        "access_time": "2026-11-20T10:30:00Z",
    }
    # Initial sync
    r1 = client.post("/api/v1/access-logs", headers=headers, json=log_entry)
    assert r1.status_code == 201

    # Retry sending same log (idempotent test)
    r2 = client.post("/api/v1/access-logs", headers=headers, json=log_entry)
    assert r2.status_code == 200

