import ipaddress
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import load_dotenv

BACKEND_ROOT = Path(__file__).resolve().parent.parent


class ConfigurationError(Exception):
    pass


@dataclass(frozen=True)
class Settings:
    supabase_url: str
    secret_key: str = field(repr=False)
    api_key: str = field(repr=False)
    host: str = "127.0.0.1"
    port: int = 5000
    timeout_ms: int = 10000
    app_env: str = "development"


def load_settings(*, require_api_key: bool = True) -> Settings:
    load_dotenv(BACKEND_ROOT / ".env", override=False)
    environment = os.getenv("APP_ENV", os.getenv("NODE_ENV", "development"))
    if environment not in {"development", "test", "production"}:
        raise ConfigurationError("APP_ENV must be development, test or production.")
    raw_url = os.getenv("SUPABASE_URL", "")
    try:
        url = urlsplit(raw_url)
        local = url.hostname in {"localhost", "127.0.0.1", "::1"}
        valid_protocol = url.scheme == "https" or (url.scheme == "http" and local and environment != "production")
        if not url.hostname or not valid_protocol or url.username or url.password or url.query or url.fragment or url.path not in {"", "/"}:
            raise ValueError
        _ = url.port
    except ValueError:
        raise ConfigurationError("SUPABASE_URL must be an HTTPS project origin (local HTTP allowed outside production).") from None
    secret = os.getenv("SUPABASE_SECRET_KEY", "").strip()
    if not re.fullmatch(r"sb_secret_[A-Za-z0-9_-]+", secret):
        raise ConfigurationError("SUPABASE_SECRET_KEY must be a backend sb_secret_ key.")
    api_key = os.getenv("BACKEND_API_KEY", "").strip()
    if require_api_key and (not re.fullmatch(r"[A-Za-z0-9_-]{32,256}", api_key) or api_key == secret):
        raise ConfigurationError("BACKEND_API_KEY must be a separate random token of at least 32 characters.")
    host = os.getenv("HOST", "127.0.0.1")
    try:
        ipaddress.ip_address(host)
        port_text = os.getenv("PORT", "5000")
        timeout_text = os.getenv("DATABASE_REQUEST_TIMEOUT_MS", "10000")
        if not re.fullmatch(r"\d+", port_text) or not re.fullmatch(r"\d+", timeout_text):
            raise ValueError
        port, timeout = int(port_text), int(timeout_text)
        if not 1 <= port <= 65535 or not 100 <= timeout <= 60000:
            raise ValueError
    except ValueError:
        raise ConfigurationError("HOST must be an IP address, PORT 1..65535, and DATABASE_REQUEST_TIMEOUT_MS 100..60000.") from None
    return Settings(f"{url.scheme}://{url.netloc}", secret, api_key, host, port, timeout, environment)
