import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest


def run_browser(api, owned=None):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js and Playwright are required for real browser tests.")
    environment = os.environ.copy()
    bundled = Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules"
    if "NODE_PATH" not in environment and bundled.is_dir():
        environment["NODE_PATH"] = str(bundled)
    if os.name == "nt" and "PLAYWRIGHT_CHANNEL" not in environment:
        chrome = Path(environment.get("ProgramFiles", "C:/Program Files")) / "Google/Chrome/Application/chrome.exe"
        edge = Path(environment.get("ProgramFiles(x86)", "C:/Program Files (x86)")) / "Microsoft/Edge/Application/msedge.exe"
        if chrome.is_file():
            environment["PLAYWRIGHT_CHANNEL"] = "chrome"
        elif edge.is_file():
            environment["PLAYWRIGHT_CHANNEL"] = "msedge"
    probe = subprocess.run([node, "-e", "require.resolve('playwright')"], env=environment, capture_output=True, timeout=15)
    if probe.returncode:
        pytest.skip("Install Playwright and Chromium to run real browser tests.")
    environment["PORTAL_BASE_URL"] = str(api.client.base_url.copy_with(path="/"))
    environment["BACKEND_API_KEY"] = api.settings.api_key
    environment["PORTAL_FIXTURE"] = json.dumps(owned) if owned else ""
    result = subprocess.run([node, str(Path(__file__).with_name("portal_browser.cjs"))], env=environment,
                            capture_output=True, text=True, timeout=240, encoding="utf-8", errors="replace")
    output = (result.stdout + result.stderr).replace(api.settings.api_key, "[redacted]").replace(api.settings.secret_key, "[redacted]")
    assert result.returncode == 0, output


def test_real_portal_browser_readonly(api):
    run_browser(api)


def test_real_portal_browser_write_workflows(api, owned):
    run_browser(api, owned)
    log = api.database.execute(api.database.client.table("access_logs").select("id").eq("id", owned["log_id"]))
    assert len(log) == 1
    embedding = api.database.execute(api.database.client.table("face_embeddings").select("model_name").eq("user_id", owned["user"]["id"]))
    assert embedding[0]["model_name"] == "portal-integration"
