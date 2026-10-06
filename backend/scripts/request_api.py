import argparse
import json
import sys
from pathlib import Path

import httpx

from app.config import ConfigurationError, load_settings


def main() -> int:
    parser = argparse.ArgumentParser(description="Call the real backend API without printing its API key.")
    parser.add_argument("method", choices=["GET", "POST", "PUT", "PATCH", "DELETE"], nargs="?", default="GET")
    parser.add_argument("path", nargs="?", default="/health")
    parser.add_argument("body", nargs="?", help="JSON text or @path/to/body.json")
    args = parser.parse_args()
    try:
        settings = load_settings()
        if not args.path.startswith("/") or args.path.startswith("//") or ".." in args.path:
            parser.error("Use a path relative to /api/v1.")
        body_text = Path(args.body[1:]).read_text(encoding="utf-8") if args.body and args.body.startswith("@") else args.body
        body = json.loads(body_text) if body_text is not None else None
        host = "127.0.0.1" if settings.host == "0.0.0.0" else "::1" if settings.host == "::" else settings.host
        address = f"[{host}]" if ":" in host else host
        with httpx.Client(timeout=30, follow_redirects=False) as client:
            kwargs = {"json": body} if body_text is not None else {}
            response = client.request(args.method, f"http://{address}:{settings.port}/api/v1{args.path}", headers={"x-api-key": settings.api_key}, **kwargs)
        print(f"HTTP {response.status_code}")
        if response.status_code != 204:
            print(json.dumps(response.json(), indent=2, ensure_ascii=False))
        return 0 if response.is_success else 1
    except ConfigurationError as error:
        print(f"[CONFIG] {error}", file=sys.stderr)
    except (httpx.HTTPError, ValueError, OSError):
        print("[API] Request failed. Start the backend and check the method, path and JSON body.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
