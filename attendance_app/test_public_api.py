"""Test the publicly exposed FaceAccess API over HTTPS.

Examples:
  python backend/scripts/test_public_api.py
  python backend/scripts/test_public_api.py --base-url https://example.trycloudflare.com --key YOUR_KEY
  set BACKEND_API_KEY=YOUR_KEY && python backend/scripts/test_public_api.py
"""

import argparse
import os
import sys
from getpass import getpass
from urllib.parse import urlsplit

import httpx


DEFAULT_BASE_URL = "https://sun-sixth-consultation-angel.trycloudflare.com"


def clean_base_url(value: str) -> str:
    value = value.strip().rstrip("/")
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise argparse.ArgumentTypeError("Base URL must be an http:// or https:// URL")
    if parsed.path and parsed.path not in {"/", ""}:
        value = f"{parsed.scheme}://{parsed.netloc}"
    return value


def print_result(name: str, response: httpx.Response) -> bool:
    print(f"\n[{name}] HTTP {response.status_code}")
    print(f"X-Request-Id: {response.headers.get('x-request-id', '-')}")
    try:
        body = response.json()
    except Exception:
        body = response.text[:500]
    if isinstance(body, dict):
        error = body.get("error")
        data = body.get("data")
        if error:
            print(f"Error: {error.get('code')} - {error.get('message')}")
        elif isinstance(data, list):
            print(f"OK: received {len(data)} item(s)")
        elif isinstance(data, dict):
            print("OK:", data)
        else:
            print("OK:", body)
    else:
        print(body)
    return response.is_success


def main() -> int:
    parser = argparse.ArgumentParser(description="Test public FaceAccess API endpoints")
    parser.add_argument("--base-url", default=os.getenv("PUBLIC_BASE_URL", DEFAULT_BASE_URL), type=clean_base_url)
    parser.add_argument("--key", default=os.getenv("BACKEND_API_KEY"), help="Backend x-api-key; prefer BACKEND_API_KEY environment variable")
    parser.add_argument("--username", default=os.getenv("ADMIN_USERNAME", "admin"))
    parser.add_argument("--password", default=os.getenv("ADMIN_PASSWORD"), help="Admin password; use prompt when omitted")
    parser.add_argument("--login", action="store_true", help="Test admin login and bearer token")
    args = parser.parse_args()

    key = args.key
    if not key:
        key = getpass("BACKEND_API_KEY (input hidden): ").strip()
    if not key:
        print("[CONFIG] A backend API key is required.", file=sys.stderr)
        return 2

    api = f"{args.base_url}/api/v1"
    all_ok = True

    try:
        with httpx.Client(timeout=15, follow_redirects=True) as client:
            all_ok &= print_result("DNS/HTTPS + public web", client.get(f"{args.base_url}/portal/"))
            all_ok &= print_result("Health check", client.get(f"{api}/health", headers={"x-api-key": key}))
            all_ok &= print_result("List users", client.get(f"{api}/users", headers={"x-api-key": key}))
            all_ok &= print_result("List devices", client.get(f"{api}/devices", headers={"x-api-key": key}))

            unauthenticated = client.get(f"{api}/users")
            print_result("Without API key (expected 401)", unauthenticated)
            all_ok &= unauthenticated.status_code == 401

            if args.login:
                password = args.password
                if password is None:
                    password = getpass("Admin password (input hidden): ").strip()
                login_response = client.post(
                    f"{api}/auth/login",
                    json={"username": args.username, "password": password},
                )
                all_ok &= print_result("Admin login", login_response)
                if login_response.is_success:
                    token = login_response.json().get("data", {}).get("access_token")
                    if not token:
                        token = login_response.json().get("data", {}).get("token")
                    if token:
                        me = client.get(f"{api}/auth/me", headers={"Authorization": f"Bearer {token}"})
                        all_ok &= print_result("Bearer auth", me)
    except httpx.HTTPError as exc:
        print(f"\n[NETWORK] Request failed: {exc}", file=sys.stderr)
        return 1

    print("\nSummary:", "PASS" if all_ok else "FAIL")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
