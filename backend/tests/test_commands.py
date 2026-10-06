import os
import socket
import subprocess
import sys
import time

import httpx

from app.config import BACKEND_ROOT, load_settings


def test_request_api_cli_uses_real_server(api):
    environment = {**os.environ, "HOST": "127.0.0.1", "PORT": str(api.client.base_url.port)}
    result = subprocess.run([sys.executable, "-m", "scripts.request_api", "GET", "/health"], cwd=BACKEND_ROOT,
                            env=environment, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0
    assert "HTTP 200" in result.stdout
    assert '"database": "connected"' in result.stdout


def test_run_entry_point_starts_real_backend_and_stops_cleanly():
    settings = load_settings()
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    environment = {**os.environ, "HOST": "127.0.0.1", "PORT": str(port)}
    process = subprocess.Popen([sys.executable, "run.py"], cwd=BACKEND_ROOT, env=environment,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        deadline = time.monotonic() + 30
        ready = False
        with httpx.Client(timeout=3, follow_redirects=False) as client:
            while process.poll() is None and time.monotonic() < deadline:
                try:
                    response = client.get(f"http://127.0.0.1:{port}/api/v1/health", headers={"x-api-key": settings.api_key})
                    ready = response.status_code == 200 and response.json()["data"]["database"] == "connected"
                    if ready:
                        break
                except httpx.HTTPError:
                    pass
                time.sleep(0.1)
        assert ready, "run.py did not start a backend connected to the real database."
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
