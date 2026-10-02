import os
import socket
import threading
import time
from dataclasses import dataclass, field
from uuid import uuid4

import httpx
import pytest
import uvicorn

from app.config import Settings, load_settings
from app.main import create_app


@dataclass
class API:
    settings: Settings = field(repr=False)
    application: object = field(repr=False)
    client: httpx.Client = field(repr=False)

    def request(self, method, path, body=None, *, authenticated=True, raw=None):
        kwargs = {}
        if raw is not None:
            kwargs["content"] = raw
            kwargs["headers"] = {"Content-Type": "application/json"}
        elif body is not None:
            kwargs["json"] = body
        headers = kwargs.setdefault("headers", {})
        if authenticated:
            headers["x-api-key"] = self.settings.api_key
        response = self.client.request(method, path, **kwargs)
        if self.settings.api_key in response.text or self.settings.secret_key in response.text:
            pytest.fail("The response exposed credentials.")
        return response

    def expect(self, method, path, body=None, status=200):
        response = self.request(method, path, body)
        if response.status_code != status:
            code = response.json().get("error", {}).get("code", "no error code")
            pytest.fail(f"{method} {path}: expected HTTP {status}, got {response.status_code} ({code}).")
        return None if status == 204 else response.json().get("data")

    @property
    def database(self):
        return self.application.state.database


@pytest.fixture(scope="module")
def api():
    settings = load_settings()
    application = create_app(settings)
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(application, log_level="critical", access_log=False, server_header=False))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 30
        while not server.started and thread.is_alive() and time.monotonic() < deadline:
            time.sleep(0.05)
        if not server.started:
            pytest.fail("Real backend startup failed; check configuration, Supabase credentials and network access.")
        with httpx.Client(base_url=f"http://127.0.0.1:{port}/api/v1", timeout=30, follow_redirects=False) as client:
            yield API(settings, application, client)
    finally:
        server.should_exit = True
        thread.join(timeout=15)
        sock.close()
        if thread.is_alive():
            pytest.fail("The integration HTTP server did not stop cleanly.")


@pytest.fixture
def owned(api):
    if os.getenv("INTEGRATION_ALLOW_WRITES") != "true":
        pytest.skip("Enable INTEGRATION_ALLOW_WRITES=true on a development Supabase project to test writes.")
    suffix = uuid4().hex
    user_codes = [f"it_{suffix}_a", f"it_{suffix}_b"]
    device_code = f"it_{suffix}"
    department = f"Integration_{suffix}"
    log_id = str(uuid4())
    try:
        users = [api.expect("POST", "/users", {"user_code": code, "full_name": f"Integration User {index}", "department": department}, 201)
                 for index, code in enumerate(user_codes)]
        device = api.expect("POST", "/devices", {"device_code": device_code, "name": "Integration Device"}, 201)
        yield {"user": users[0], "second_user": users[1], "device": device, "department": department, "log_id": log_id}
    finally:
        db = api.database
        users = db.execute(db.client.table("users").select("id").in_("user_code", user_codes))
        ids = [user["id"] for user in users]
        db.execute(db.client.table("access_logs").delete().eq("id", log_id))
        if ids:
            db.execute(db.client.table("registration_sessions").delete().in_("user_id", ids))
            db.execute(db.client.table("face_embeddings").delete().in_("user_id", ids))
        db.execute(db.client.table("users").delete().in_("user_code", user_codes))
        db.execute(db.client.table("devices").delete().eq("device_code", device_code))
        remaining = db.execute(db.client.table("users").select("id").in_("user_code", user_codes))
        remaining += db.execute(db.client.table("devices").select("id").eq("device_code", device_code))
        remaining += db.execute(db.client.table("access_logs").select("id").eq("id", log_id))
        if remaining:
            pytest.fail("Owned integration fixtures were not completely removed.")
