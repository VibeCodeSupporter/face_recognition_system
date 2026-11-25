from __future__ import annotations

from uuid import UUID

from fastapi import Request

from app.errors import AppError

ROLE_ADMIN = "admin"
ROLE_OPERATOR = "operator"

ROLE_PERMISSIONS: dict[str, list[str]] = {
    ROLE_ADMIN: ["*"],
    ROLE_OPERATOR: [
        "users:create",
        "users:read",
        "users:search",
        "embeddings:read",
        "embeddings:create",
        "devices:read",
        "devices:search",
        "sessions:create",
        "sessions:read",
        "sessions:search",
        "logs:read",
        "logs:search",
        "logs:export",
    ],
}


def get_permissions_for_role(role: str | None) -> list[str]:
    """Return canonical permission keys for the given account role."""
    return list(ROLE_PERMISSIONS.get(role or "", ROLE_PERMISSIONS[ROLE_OPERATOR]))


def get_actor(request: Request) -> dict | None:
    """Return the authenticated JWT admin payload, or None when using machine x-api-key."""
    return getattr(request.state, "admin", None)


def require_super_admin(request: Request) -> None:
    """Block non-admin JWT accounts from mutating or deleting protected resources."""
    actor = get_actor(request)
    if actor is not None and actor.get("role") != ROLE_ADMIN:
        raise AppError(
            403,
            "FORBIDDEN",
            "Tài khoản của bạn không có quyền thực hiện thao tác này. Chỉ Quản trị viên Cấp cao mới được phép.",
        )


def require_add_embedding_or_admin(record_id: UUID, request: Request) -> None:
    """Allow super admin full access; allow operator ONLY to add an embedding when none exists yet."""
    actor = get_actor(request)
    if actor is not None and actor.get("role") != ROLE_ADMIN:
        try:
            request.app.state.services.embeddings.get(str(record_id))
            raise AppError(
                403,
                "FORBIDDEN",
                "Tài khoản vận hành chỉ được phép thêm vector khuôn mặt mới, không được ghi đè vector đã có.",
            )
        except AppError as err:
            if err.code != "NOT_FOUND":
                raise

def require_permission(permission: str):
    def _checker(request: Request) -> None:
        actor = get_actor(request)
        if actor is None:
            return  # x-api-key giữ toàn quyền
        role = actor.get("role")
        perms = get_permissions_for_role(role)
        if "*" not in perms and permission not in perms:
            raise AppError(403, "FORBIDDEN", "Tài khoản của bạn không có quyền thực hiện thao tác này.")
    return _checker