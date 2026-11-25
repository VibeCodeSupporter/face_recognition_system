from __future__ import annotations

import json
import tempfile
from pathlib import Path
from uuid import uuid4

import pytest
from starlette.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.repositories import Repositories
from app.services import Services
from scripts.simulate_device import (
    InMemoryDB,
    MockAccessLogRepo,
    MockEmbeddingRepo,
    MockSessionRepo,
    MockTableRepo,
)


@pytest.fixture
def rbac_ctx(tmp_path: Path):
    settings = Settings(
        supabase_url="https://mock.supabase.co",
        secret_key="sb_secret_mock",
        api_key="a" * 32,
        host="127.0.0.1",
        port=5000,
        jwt_secret="jwt_secret_for_tests_32_characters_minimum",
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
    services = Services(repos, settings)
    services.auth.admin_file = tmp_path / "admins.json"
    services.deletion_history.history_file = tmp_path / "deletion_history.json"
    app.state.services = services

    # Seed sample users, devices, sessions, and logs across hours/days/months
    u_no_face = str(uuid4())
    u_with_face = str(uuid4())
    d_id = str(uuid4())
    s_id = str(uuid4())

    repos.users.insert({"id": u_no_face, "user_code": "NV001", "full_name": "Chưa Có Mặt", "status": "active"})
    repos.users.insert({"id": u_with_face, "user_code": "NV002", "full_name": "Đã Có Mặt", "status": "active"})
    repos.embeddings.upsert({
        "user_id": u_with_face,
        "model_name": "GhostFaceNet",
        "model_version": "v1",
        "dimension": 3,
        "embedding_data": [0.1, 0.2, 0.3],
    })
    repos.devices.insert({
        "id": d_id,
        "device_code": "DOOR_01",
        "name": "Cửa chính",
        "status": "online",
        "api_key_hash": "hash",
    })
    repos.sessions.insert({
        "id": s_id,
        "user_id": u_no_face,
        "device_id": d_id,
        "status": "pending",
        "expires_at": "2029-01-01T00:00:00Z",
    })

    # Seed logs: 10:15, 10:45 on 2026-11-25 (UTC+7), 15:00 on 2026-11-25, and 2026-10-15
    logs_seed = [
        (str(uuid4()), u_with_face, "granted", "2026-11-25T10:15:00+07:00"),
        (str(uuid4()), None, "denied", "2026-11-25T10:45:00+07:00"),
        (str(uuid4()), u_with_face, "granted", "2026-11-25T15:00:00+07:00"),
        (str(uuid4()), u_with_face, "granted", "2026-10-15T09:00:00+07:00"),
    ]
    for lid, uid, result, ts in logs_seed:
        repos.logs.insert({
            "id": lid,
            "user_id": uid,
            "device_id": d_id,
            "result": result,
            "confidence": 95.0 if uid else 10.0,
            "access_time": ts,
            "synced_at": ts,
        })

    client = TestClient(app)

    admin_login = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    assert admin_login.status_code == 200
    admin_data = admin_login.json()["data"]

    op_login = client.post("/api/v1/auth/login", json={"username": "operator", "password": "operator123"})
    assert op_login.status_code == 200
    op_data = op_login.json()["data"]

    return {
        "client": client,
        "admin_headers": {"Authorization": f"Bearer {admin_data['token']}"},
        "operator_headers": {"Authorization": f"Bearer {op_data['token']}"},
        "admin_info": admin_data["admin"],
        "operator_info": op_data["admin"],
        "u_no_face": u_no_face,
        "u_with_face": u_with_face,
        "device_id": d_id,
        "session_id": s_id,
    }


def test_two_accounts_roles_and_permissions(rbac_ctx):
    assert rbac_ctx["admin_info"]["role"] == "admin"
    assert "*" in rbac_ctx["admin_info"]["permissions"]
    assert rbac_ctx["operator_info"]["role"] == "operator"
    assert "embeddings:create" in rbac_ctx["operator_info"]["permissions"]
    assert "users:create" not in rbac_ctx["operator_info"]["permissions"]

    client = rbac_ctx["client"]
    op_me = client.get("/api/v1/auth/me", headers=rbac_ctx["operator_headers"])
    assert op_me.status_code == 200
    assert op_me.json()["data"]["role"] == "operator"


def test_operator_can_view_search_and_add_new_embedding_only(rbac_ctx):
    client = rbac_ctx["client"]
    op_h = rbac_ctx["operator_headers"]
    u_no_face = rbac_ctx["u_no_face"]
    u_with_face = rbac_ctx["u_with_face"]
    d_id = rbac_ctx["device_id"]
    s_id = rbac_ctx["session_id"]

    # Read & search endpoints succeed for operator
    assert client.get("/api/v1/users", headers=op_h).status_code == 200
    assert client.get(f"/api/v1/users/{u_no_face}", headers=op_h).status_code == 200
    assert client.get("/api/v1/devices?device_code=DOOR_01", headers=op_h).status_code == 200
    assert client.get(f"/api/v1/devices/{d_id}", headers=op_h).status_code == 200
    assert client.get("/api/v1/registration-sessions?status=pending", headers=op_h).status_code == 200
    assert client.get(f"/api/v1/registration-sessions/{s_id}", headers=op_h).status_code == 200
    assert client.get("/api/v1/access-logs", headers=op_h).status_code == 200
    assert client.get(f"/api/v1/users/{u_with_face}/face-embedding", headers=op_h).status_code == 200

    # Operator CAN add embedding for user without embedding
    emb_payload = {"model_name": "Facenet512", "model_version": "v1", "dimension": 3, "embedding_data": [0.2, 0.3, 0.4]}
    assert client.put(f"/api/v1/users/{u_no_face}/face-embedding", headers=op_h, json=emb_payload).status_code == 200

    # Operator CANNOT overwrite an existing embedding
    overwrite = client.put(f"/api/v1/users/{u_with_face}/face-embedding", headers=op_h, json=emb_payload)
    assert overwrite.status_code == 403
    assert overwrite.json()["error"]["code"] == "FORBIDDEN"

    # Operator CANNOT delete embeddings, or create/update/delete users, devices, sessions, or logs
    forbidden_calls = [
        ("POST", "/api/v1/users", {"user_code": "NV999", "full_name": "Blocked"}),
        ("PATCH", f"/api/v1/users/{u_no_face}", {"full_name": "Hacked"}),
        ("DELETE", f"/api/v1/users/{u_no_face}", None),
        ("DELETE", f"/api/v1/users/{u_with_face}/face-embedding", None),
        ("POST", "/api/v1/devices", {"device_code": "D99", "name": "Blocked"}),
        ("PATCH", f"/api/v1/devices/{d_id}", {"name": "Hacked"}),
        ("DELETE", f"/api/v1/devices/{d_id}", None),
        ("POST", "/api/v1/registration-sessions", {"user_id": u_no_face, "device_id": d_id, "expires_at": "2029-01-01T00:00:00Z"}),
        ("PATCH", f"/api/v1/registration-sessions/{s_id}", {"status": "cancelled"}),
        ("DELETE", f"/api/v1/registration-sessions/{s_id}", None),
        ("DELETE", "/api/v1/access-logs?start_time=2026-11-25T00:00:00Z&end_time=2026-11-25T23:59:59Z", None),
    ]
    for method, path, body in forbidden_calls:
        res = client.request(method, path, headers=op_h, json=body)
        assert res.status_code == 403, f"Expected 403 for {method} {path}, got {res.status_code}"
        assert res.json()["error"]["code"] == "FORBIDDEN"


def test_admin_can_crud_all_and_query_or_delete_logs_by_time_range(rbac_ctx):
    client = rbac_ctx["client"]
    adm_h = rbac_ctx["admin_headers"]

    # Admin CAN query logs by time range (10:00..11:00 UTC+7 on 2026-11-25 -> 2 logs)
    res_hour = client.get(
        "/api/v1/access-logs",
        headers=adm_h,
        params={
            "start_time": "2026-11-25T10:00:00.000+07:00",
            "end_time": "2026-11-25T10:59:59.999+07:00",
        },
    )
    assert res_hour.status_code == 200
    assert len(res_hour.json()["data"]["items"]) == 2

    # Invalid range (start > end) returns 400 VALIDATION_ERROR
    bad_range = client.get(
        "/api/v1/access-logs",
        headers=adm_h,
        params={
            "start_time": "2026-11-26T00:00:00Z",
            "end_time": "2026-11-25T00:00:00Z",
        },
    )
    assert bad_range.status_code == 400

    # Delete logs by hour and verify WebSocket LOGS_DELETED broadcast
    with client.websocket_connect("/api/v1/ws/portal") as portal_ws:
        del_hour = client.delete(
            "/api/v1/access-logs",
            headers=adm_h,
            params={
                "start_time": "2026-11-25T10:00:00.000+07:00",
                "end_time": "2026-11-25T10:59:59.999+07:00",
            },
        )
        assert del_hour.status_code == 200
        assert del_hour.json()["data"]["deleted_count"] == 2
        ws_events = [json.loads(portal_ws.receive_text()), json.loads(portal_ws.receive_text())]
        events_by_name = {ev["event"]: ev for ev in ws_events}
        assert "DELETION_HISTORY_CREATED" in events_by_name
        assert events_by_name["LOGS_DELETED"]["deleted_count"] == 2

    # Remaining logs count is 2 (15:00 on 2026-11-25 and 2026-10-15)
    remaining_nov = client.get(
        "/api/v1/access-logs",
        headers=adm_h,
        params={"start_time": "2026-11-01T00:00:00+07:00", "end_time": "2026-11-30T23:59:59+07:00"},
    )
    assert len(remaining_nov.json()["data"]["items"]) == 1

    # Delete remaining November logs by day
    del_day = client.delete(
        "/api/v1/access-logs",
        headers=adm_h,
        params={
            "start_time": "2026-11-25T00:00:00.000+07:00",
            "end_time": "2026-11-25T23:59:59.999+07:00",
        },
    )
    assert del_day.status_code == 200
    assert del_day.json()["data"]["deleted_count"] == 1

    # Delete October logs by month
    del_month = client.delete(
        "/api/v1/access-logs",
        headers=adm_h,
        params={
            "start_time": "2026-10-01T00:00:00.000+07:00",
            "end_time": "2026-10-31T23:59:59.999+07:00",
        },
    )
    assert del_month.status_code == 200
    assert del_month.json()["data"]["deleted_count"] == 1
    assert len(client.get("/api/v1/access-logs", headers=adm_h).json()["data"]["items"]) == 0

    # Admin CAN update/overwrite embedding and create/delete users and sessions
    u_id = rbac_ctx["u_with_face"]
    assert client.put(
        f"/api/v1/users/{u_id}/face-embedding",
        headers=adm_h,
        json={"model_name": "GhostFaceNet", "model_version": "v2", "dimension": 2, "embedding_data": [0.9, 0.8]},
    ).status_code == 200
    assert client.delete(f"/api/v1/registration-sessions/{rbac_ctx['session_id']}", headers=adm_h).status_code == 204
    new_u = client.post("/api/v1/users", headers=adm_h, json={"user_code": "NV_NEW", "full_name": "Mới Tạo"})
    assert new_u.status_code == 201
    assert client.delete(f"/api/v1/users/{new_u.json()['data']['id']}", headers=adm_h).status_code == 204


def test_embedding_auto_completes_and_deletes_session_plus_deletion_history(rbac_ctx):
    client = rbac_ctx["client"]
    adm_h = rbac_ctx["admin_headers"]
    op_h = rbac_ctx["operator_headers"]
    u_no_face = rbac_ctx["u_no_face"]
    s_id = rbac_ctx["session_id"]

    # Operator adds embedding for u_no_face -> auto-completes & deletes pending session s_id
    emb_payload = {"model_name": "Facenet512", "model_version": "v1", "dimension": 3, "embedding_data": [0.2, 0.3, 0.4]}
    res = client.put(f"/api/v1/users/{u_no_face}/face-embedding", headers=op_h, json=emb_payload)
    assert res.status_code == 200
    assert client.get(f"/api/v1/registration-sessions/{s_id}", headers=adm_h).status_code == 404

    # Delete access logs and a device to populate deletion history
    assert client.delete(
        "/api/v1/access-logs",
        headers=adm_h,
        params={"start_time": "2026-01-01T00:00:00Z", "end_time": "2027-01-01T00:00:00Z"},
    ).status_code == 200
    assert client.delete(f"/api/v1/devices/{rbac_ctx['device_id']}", headers=adm_h).status_code == 204

    # Both operator and admin can query deletion history by entity_type & search
    hist_all = client.get("/api/v1/deletion-history", headers=op_h)
    assert hist_all.status_code == 200
    items = hist_all.json()["data"]["items"]
    types = {item["entity_type"] for item in items}
    assert {"session", "access_log", "device"} <= types

    hist_sess = client.get("/api/v1/deletion-history?entity_type=session", headers=op_h)
    assert hist_sess.status_code == 200
    assert len(hist_sess.json()["data"]["items"]) == 1
    assert hist_sess.json()["data"]["items"][0]["entity_id"] == s_id
    assert hist_sess.json()["data"]["items"][0]["snapshot"]["status"] == "completed"

    # Operator cannot clear deletion history; admin can
    assert client.delete("/api/v1/deletion-history", headers=op_h).status_code == 403
    cleared = client.delete("/api/v1/deletion-history", headers=adm_h)
    assert cleared.status_code == 200
    assert cleared.json()["data"]["cleared_count"] >= 6

