import hashlib
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from uuid import uuid4


def session(api, owned):
    return api.expect("POST", "/registration-sessions", {"user_id": owned["user"]["id"], "device_id": owned["device"]["id"]}, 201)


def embedding(api, owned, **overrides):
    values = {"model_name": "integration-model", "model_version": "1", "dimension": 3, "embedding_data": [0.1, 0.2, 0.3], **overrides}
    return api.expect("PUT", f"/users/{owned['user']['id']}/face-embedding", values)


def log(owned):
    return {"id": owned["log_id"], "user_id": owned["user"]["id"], "device_id": owned["device"]["id"], "result": "granted",
            "confidence": 99.3, "access_time": datetime.now(timezone.utc).isoformat(timespec="milliseconds")}


def test_real_schema(api):
    report = api.database.check()
    assert len(report) == 5
    assert all(item["ok"] for item in report)


def test_real_health(api):
    assert api.expect("GET", "/health") == {"status": "ok", "database": "connected"}


def test_authentication(api):
    response = api.request("GET", "/users", authenticated=False)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"
    response = api.client.get("/users", headers={"x-api-key": "invalid"})
    assert response.status_code == 401


def test_dto_and_readonly_fields(api):
    response = api.request("POST", "/users", {"full_name": "Validation", "api_key_hash": "forbidden"})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_validation_error_identifies_missing_field(api):
    response = api.request("POST", "/users", {"full_name": "Validation only"})
    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert error["details"] == [{"path": "body.user_code", "message": "Field required"}]
    assert error["request_id"] == response.headers["x-request-id"]


def test_invalid_parameters(api):
    for path in ("/users?limit=0", "/devices?offset=-1", "/users/not-a-uuid", "/users?unexpected=1", "/users?limit=1.0"):
        api.expect("GET", path, status=400)


def test_missing_resource_and_route(api):
    api.expect("GET", f"/users/{uuid4()}", status=404)
    api.expect("GET", "/not-a-route", status=404)


def test_invalid_json_and_body_limit(api):
    response = api.request("POST", "/users", raw="{bad-json")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_JSON"
    response = api.request("POST", "/users", {"full_name": "x" * 140000})
    assert response.status_code == 413


def test_real_lists_pagination_and_security_headers(api):
    missing = uuid4()
    for path in (f"/users?department=it_{missing.hex}", f"/devices?device_code=it_{missing.hex}",
                 f"/registration-sessions?user_id={missing}", f"/access-logs?device_id={missing}"):
        response = api.request("GET", path)
        assert response.status_code == 200
        expected = [] if path.startswith("/users?") else {"items": [], "limit": 20, "offset": 0, "has_more": False}
        assert response.json()["data"] == expected
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["x-request-id"]


def test_openapi_has_dtos_and_api_key_security(api):
    response = api.client.get(api.client.base_url.copy_with(path="/openapi.json"))
    assert response.status_code == 200
    schema = response.json()
    assert "UserCreate" in schema["components"]["schemas"]
    assert "FaceEmbeddingPut" in schema["components"]["schemas"]
    assert schema["components"]["securitySchemes"]["APIKeyHeader"]["name"] == "x-api-key"
    assert schema["paths"]["/api/v1/users"]["post"]["security"]
    assert "HTTPValidationError" not in schema["components"]["schemas"]
    for path in schema["paths"].values():
        for operation in path.values():
            responses = operation["responses"]
            for status in ("400", "401", "422"):
                assert responses[status]["content"]["application/json"]["schema"]["$ref"] == "#/components/schemas/ErrorResponse"
            assert responses["422"]["description"] != "Validation Error"
    example = schema["components"]["schemas"]["UserCreate"]["example"]
    assert set(example) == {"user_code", "full_name"}
    assert example["user_code"] != "string"


def test_create_users_are_persisted_in_supabase(api, owned):
    user = owned["user"]
    result = api.database.execute(api.database.client.table("users").select("user_code").eq("id", user["id"]))
    assert result[0]["user_code"] == user["user_code"]


def test_user_crud_unique_and_patch(api, owned):
    user = owned["user"]
    assert api.expect("GET", f"/users/{user['id']}")["user_code"] == user["user_code"]
    api.expect("POST", "/users", {"user_code": user["user_code"], "full_name": "Duplicate"}, 409)
    assert api.expect("PATCH", f"/users/{user['id']}", {"phone": "0900000000", "email": None})["phone"] == "0900000000"
    for body in ({}, {"id": str(uuid4())}, {"full_name": None}, {"user_code": 123}):
        api.expect("PATCH", f"/users/{user['id']}", body, 400)


def test_real_users_all_matching_rows(api, owned):
    users = api.expect("GET", f"/users?department={owned['department']}")
    assert isinstance(users, list)
    assert {user["id"] for user in users} == {owned["user"]["id"], owned["second_user"]["id"]}
    api.expect("GET", "/users?limit=1", status=400)


def test_portal_static_assets_do_not_expose_database_or_credentials(api):
    for path in ("/portal/", "/portal/js/api.js", "/portal/js/forms.js", "/portal/js/app.js", "/portal/css/style.css"):
        response = api.client.get(api.client.base_url.copy_with(path=path))
        assert response.status_code == 200
        assert api.settings.api_key not in response.text
        assert api.settings.secret_key not in response.text
        assert response.headers["cache-control"] == "no-store"
    for path in ("/users", "/devices", "/registration-sessions", "/access-logs", "/health"):
        assert api.request("GET", path, authenticated=False).status_code == 401


def test_device_token_hash_is_private(api, owned):
    device = owned["device"]
    assert len(device["device_token"]) == 64
    assert "api_key_hash" not in device
    row = api.database.execute(api.database.client.table("devices").select("api_key_hash").eq("id", device["id"]))[0]
    assert row["api_key_hash"] == hashlib.sha256(device["device_token"].encode()).hexdigest()
    result = api.expect("GET", f"/devices/{device['id']}")
    assert "api_key_hash" not in result and "device_token" not in result


def test_device_dto_and_settings(api, owned):
    device = owned["device"]
    api.expect("POST", "/devices", {"device_code": device["device_code"], "name": "Duplicate"}, 409)
    result = api.expect("PATCH", f"/devices/{device['id']}", {"settings": {"threshold": 85, "doorDuration": 4, "liveness": True}, "status": "online"})
    assert result["settings"]["threshold"] == 85
    for body in ({"api_key_hash": "forbidden"}, {"settings": {"threshold": 200}}, {"settings": None}):
        api.expect("PATCH", f"/devices/{device['id']}", body, 400)


def test_session_references_and_fk_restrict(api, owned):
    pending = session(api, owned)
    assert pending["status"] == "pending"
    api.expect("POST", "/registration-sessions", {"user_id": str(uuid4()), "device_id": owned["device"]["id"]}, 404)
    api.expect("DELETE", f"/users/{owned['user']['id']}", status=409)
    api.expect("DELETE", f"/devices/{owned['device']['id']}", status=409)
    api.expect("PATCH", f"/registration-sessions/{pending['id']}", {"status": "completed"}, 409)


def test_vector_dimension_and_real_persistence(api, owned):
    path = f"/users/{owned['user']['id']}/face-embedding"
    api.expect("PUT", path, {"model_name": "integration-model", "model_version": "1", "dimension": 3, "embedding_data": [0.1, 0.2]}, 400)
    api.expect("GET", path, status=404)
    assert embedding(api, owned)["embedding_data"] == [0.1, 0.2, 0.3]
    read = api.expect("GET", path)
    assert read["dimension"] == 3 and read["user_id"] == owned["user"]["id"]
    api.expect("PUT", path, {"model_name": "integration-model", "model_version": "1", "dimension": 1, "embedding_data": ["0.1"]}, 400)


def test_vector_put_replaces_not_duplicates(api, owned):
    embedding(api, owned)
    assert embedding(api, owned, model_version="2", dimension=2, embedding_data=[0.4, 0.5])["model_version"] == "2"
    rows = api.database.execute(api.database.client.table("face_embeddings").select("user_id").eq("user_id", owned["user"]["id"]))
    assert len(rows) == 1


def test_session_completion_and_terminal_state(api, owned):
    pending = session(api, owned)
    embedding(api, owned)
    completed = api.expect("PATCH", f"/registration-sessions/{pending['id']}", {"status": "completed"})
    assert completed["status"] == "completed" and completed["completed_at"]
    api.expect("PATCH", f"/registration-sessions/{pending['id']}", {"status": "cancelled"}, 409)


def test_inactive_user_and_expired_input(api, owned):
    api.expect("PATCH", f"/users/{owned['user']['id']}", {"status": "inactive"})
    api.expect("POST", "/registration-sessions", {"user_id": owned["user"]["id"], "device_id": owned["device"]["id"]}, 409)
    api.expect("POST", "/registration-sessions", {"user_id": owned["user"]["id"], "device_id": owned["device"]["id"], "expires_at": "2000-01-01T00:00:00Z"}, 400)


def test_session_cancellation(api, owned):
    pending = session(api, owned)
    cancelled = api.expect("PATCH", f"/registration-sessions/{pending['id']}", {"status": "cancelled"})
    assert cancelled["status"] == "cancelled" and cancelled["completed_at"] is None


def test_concurrent_session_finalization(api, owned):
    pending = session(api, owned)
    path = f"/registration-sessions/{pending['id']}"
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda status: api.request("PATCH", path, {"status": status}).status_code, ["cancelled", "failed"]))
    assert sorted(results) == [200, 409]


def test_real_logs_idempotent_retry(api, owned):
    event = log(owned)
    api.expect("POST", "/access-logs", event, 201)
    api.expect("POST", "/access-logs", event, 200)
    assert api.expect("GET", f"/access-logs/{owned['log_id']}")["user_id"] == owned["user"]["id"]
    assert len(api.expect("GET", f"/access-logs?user_id={owned['user']['id']}")["items"]) == 1


def test_log_id_cannot_overwrite_event(api, owned):
    event = log(owned)
    api.expect("POST", "/access-logs", event, 201)
    api.expect("POST", "/access-logs", {**event, "result": "denied"}, 409)
    api.expect("POST", "/access-logs", {**event, "confidence": 0.3}, 409)
    assert api.expect("GET", f"/access-logs/{owned['log_id']}")["result"] == "granted"
    api.expect("PATCH", f"/access-logs/{owned['log_id']}", {"result": "denied"}, 404)
    api.expect("DELETE", f"/access-logs/{owned['log_id']}", status=404)


def test_log_dto_and_fk(api, owned):
    event = log(owned)
    api.expect("POST", "/access-logs", {**event, "user_id": None}, 400)
    api.expect("POST", "/access-logs", {**event, "confidence": 101}, 400)
    api.expect("POST", "/access-logs", {**event, "device_id": str(uuid4())}, 409)


def test_vector_and_session_delete(api, owned):
    embedding(api, owned)
    pending = session(api, owned)
    api.expect("DELETE", f"/users/{owned['user']['id']}/face-embedding", status=204)
    api.expect("GET", f"/users/{owned['user']['id']}/face-embedding", status=404)
    api.expect("DELETE", f"/registration-sessions/{pending['id']}", status=204)
    api.expect("GET", f"/registration-sessions/{pending['id']}", status=404)


def test_user_and_device_delete_without_dependencies(api, owned):
    api.expect("DELETE", f"/users/{owned['user']['id']}", status=204)
    api.expect("DELETE", f"/users/{owned['second_user']['id']}", status=204)
    api.expect("DELETE", f"/devices/{owned['device']['id']}", status=204)
    api.expect("GET", f"/users/{owned['user']['id']}", status=404)
    api.expect("GET", f"/devices/{owned['device']['id']}", status=404)
