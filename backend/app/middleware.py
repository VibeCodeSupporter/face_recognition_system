import hashlib
import hmac
from uuid import uuid4

from starlette.responses import JSONResponse


class RequestGuard:
    def __init__(self, app, api_key: str, jwt_secret: str = ""):
        self.app = app
        self.expected = hashlib.sha256(api_key.encode()).digest()
        self.jwt_secret = jwt_secret or api_key

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_id = str(uuid4())
        scope.setdefault("state", {})["request_id"] = request_id

        async def secure_send(message):
            if message["type"] == "http.response.start":
                protected = {b"x-request-id", b"cache-control", b"x-content-type-options"}
                headers = [(name, value) for name, value in message.get("headers", []) if name.lower() not in protected]
                message["headers"] = [*headers,
                    (b"x-request-id", request_id.encode()), (b"cache-control", b"no-store"),
                    (b"x-content-type-options", b"nosniff")]
            await send(message)

        async def reject(status, code, message):
            response = JSONResponse({"error": {"code": code, "message": message, "request_id": request_id}}, status_code=status)
            await response(scope, receive, secure_send)

        path = scope["path"]
        method = scope["method"]
        is_api = path.startswith("/api/")
        public_docs = path in {"/docs", "/redoc", "/openapi.json", "/docs/oauth2-redirect"}
        public_static = (not is_api) and method in {"GET", "HEAD"}
        public_auth = path == "/api/v1/auth/login" and method == "POST"

        if not (public_docs or public_static or public_auth):
            authenticated = False
            # 1. Check Bearer token
            auth_headers = [value for name, value in scope["headers"] if name.lower() == b"authorization"]
            if auth_headers:
                auth_str = auth_headers[0].decode("latin1").strip()
                if auth_str.lower().startswith("bearer "):
                    token = auth_str[7:].strip()
                    try:
                        import jwt
                        payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
                        scope.setdefault("state", {})["admin"] = payload
                        authenticated = True
                    except Exception:
                        await reject(401, "UNAUTHORIZED", "Token xác thực không hợp lệ hoặc đã hết hạn.")
                        return

            # 2. Check x-api-key
            if not authenticated:
                keys = [value for name, value in scope["headers"] if name.lower() == b"x-api-key"]
                actual = hashlib.sha256(keys[0] if len(keys) == 1 else b"").digest()
                if hmac.compare_digest(actual, self.expected):
                    authenticated = True

            if not authenticated:
                await reject(401, "UNAUTHORIZED", "A valid backend x-api-key or Admin Bearer token is required.")
                return
        chunks, length = [], 0
        while True:
            event = await receive()
            if event["type"] == "http.disconnect":
                return
            length += len(event.get("body", b""))
            if length > 128 * 1024:
                await reject(413, "BODY_TOO_LARGE", "The JSON body must not exceed 128 KB.")
                return
            chunks.append(event.get("body", b""))
            if not event.get("more_body", False):
                break
        body = b"".join(chunks)
        replayed = False

        async def replay_receive():
            nonlocal replayed
            if not replayed:
                replayed = True
                return {"type": "http.request", "body": body, "more_body": False}
            return await receive()

        await self.app(scope, replay_receive, secure_send)
