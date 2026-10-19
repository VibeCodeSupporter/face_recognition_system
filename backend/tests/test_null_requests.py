from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import Settings
from app.dto.access_logs import AccessLogCreate
from app.main import create_app


@pytest.fixture
def client():
    api_key = "a" * 32
    app = create_app(Settings("https://example.supabase.co", "sb_secret_dummy", api_key))
    client = TestClient(app, headers={"x-api-key": api_key})
    yield client
    client.close()


@pytest.mark.parametrize("method,path", [
    ("POST", "/users"),
    ("POST", "/devices"),
    ("PATCH", "/users/00000000-0000-4000-8000-000000000001"),
    ("PATCH", "/devices/00000000-0000-4000-8000-000000000001"),
])
def test_null_user_or_device_body_returns_validation_error(client, method, path):
    response = client.request(method, f"/api/v1{path}", content="null", headers={"content-type": "application/json"})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert response.json()["error"]["details"] == [
        {"path": "body", "message": "Request body must be a JSON object."}
    ]
    assert response.json()["error"]["request_id"] == response.headers["x-request-id"]


@pytest.mark.parametrize("path,body,field", [
    ("/users", {"user_code": None, "full_name": "Test"}, "user_code"),
    ("/devices", {"device_code": None, "name": "Test"}, "device_code"),
    ("/registration-sessions", {"user_id": None, "device_id": str(uuid4())}, "user_id"),
    ("/registration-sessions", {"user_id": str(uuid4()), "device_id": None}, "device_id"),
])
def test_required_user_or_device_field_cannot_be_null(client, path, body, field):
    response = client.post(f"/api/v1{path}", json=body)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert any(detail["path"] == f"body.{field}" for detail in response.json()["error"]["details"])


def test_access_log_allows_null_user_only_for_denied_result():
    body = {
        "id": str(uuid4()),
        "user_id": None,
        "device_id": str(uuid4()),
        "result": "denied",
        "access_time": datetime.now(timezone.utc).isoformat(),
    }

    assert AccessLogCreate.model_validate(body).user_id is None
    with pytest.raises(ValidationError):
        AccessLogCreate.model_validate({**body, "result": "granted"})
    with pytest.raises(ValidationError):
        AccessLogCreate.model_validate({**body, "device_id": None})
