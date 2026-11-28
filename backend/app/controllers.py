import json
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, Security, WebSocket, WebSocketDisconnect
from fastapi.security import APIKeyHeader

from app.websocket_manager import manager as ws_manager
from app.dto.access_logs import AccessLogCreate, AccessLogDeleteQuery, AccessLogQuery

from app.dto.auth import LoginRequest, ProfileUpdateRequest

from app.dto.deletion_history import DeletionHistoryQuery
from app.dto.devices import DeviceCreate, DevicePatch, DeviceQuery
from app.dto.face_embeddings import FaceEmbeddingPut
from app.dto.registration_sessions import SessionCreate, SessionPatch, SessionQuery
from app.dto.users import UserCreate, UserPatch, UserQuery
from app.rbac import *


def _actor_label(request: Request) -> str:
    actor = get_actor(request)
    if actor:
        name = actor.get("full_name") or ""
        username = actor.get("sub") or "admin"
        return f"{username} ({name})".strip() if name else username
    return "Hệ thống / Thiết bị (API Key)"

router = APIRouter(prefix="/api/v1", dependencies=[Security(APIKeyHeader(name="x-api-key", auto_error=False))])
ws_router = APIRouter(prefix="/api/v1")



#======================================AUTH=========================================

@router.post("/auth/login", tags=["Auth"])
def login(request: Request, body: LoginRequest):
    return {"data": request.app.state.services.auth.login(body.username, body.password)}


@router.get("/auth/me", tags=["Auth"])
def get_me(request: Request):
    admin = getattr(request.state, "admin", None)
    if not admin:
        auth_header = request.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()
            admin = request.app.state.services.auth.verify_token(token)
    if not admin:
        from app.errors import AppError
        raise AppError(401, "UNAUTHORIZED", "Yêu cầu đăng nhập quản trị viên.")
    role = admin.get("role", "admin")
    return {
        "data": {
            "username": admin.get("sub", "admin"),
            "full_name": admin.get("full_name", "Quản trị viên"),
            "role": role,
            "permissions": get_permissions_for_role(role),
        }
    }


@router.patch("/auth/profile", tags=["Auth"])
def update_profile(request: Request, body: ProfileUpdateRequest):
    admin = getattr(request.state, "admin", None)
    if not admin:
        auth_header = request.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()
            admin = request.app.state.services.auth.verify_token(token)
    if not admin:
        from app.errors import AppError
        raise AppError(401, "UNAUTHORIZED", "Yêu cầu đăng nhập quản trị viên.")
    username = admin.get("sub", "admin")
    updated = request.app.state.services.auth.update_profile(
        username, full_name=body.full_name, new_password=body.new_password
    )
    return {"data": updated}


@router.post("/auth/logout", tags=["Auth"])
def logout():
    return {"data": {"message": "Đã đăng xuất thành công."}}



@router.get("/health", tags=["Health"])
def health(request: Request):
    request.app.state.database.check()
    return {"data": {"status": "ok", "database": "connected"}}

#======================================USERS========================================

@router.get("/users", tags=["Users"])
def list_users(request: Request, query: Annotated[UserQuery, Query()]):
    filters = query.model_dump(mode="json", exclude_none=True)
    users = request.app.state.services.users.list_all(filters)
    return {"data": users}
 

@router.post("/users", status_code=201, tags=["Users"], dependencies=[Depends(require_permission("users:create"))])
def create_user(request: Request, body: UserCreate):
    return {"data": request.app.state.services.users.create(body.payload())}


@router.get("/users/{record_id}", tags=["Users"])
def get_user(record_id: UUID, request: Request):
    return {"data": request.app.state.services.users.get(str(record_id))}


@router.patch("/users/{record_id}", tags=["Users"], dependencies=[Depends(require_super_admin)])
def update_user(record_id: UUID, request: Request, body: UserPatch):
    return {"data": request.app.state.services.users.update(str(record_id), body.payload())}


@router.delete("/users/{record_id}", status_code=204, tags=["Users"], dependencies=[Depends(require_super_admin)])
async def delete_user(record_id: UUID, request: Request):
    services = request.app.state.services
    user = services.users.get(str(record_id))
    services.users.remove(str(record_id))
    services.deletion_history.record(
        entity_type="user",
        entity_id=str(record_id),
        title=f"[{user.get('user_code', '')}] {user.get('full_name', '')}".strip(),
        reason="Xóa người dùng thủ công",
        deleted_by=_actor_label(request),
        snapshot=user,
    )
    await ws_manager.broadcast_to_portal({"event": "DELETION_HISTORY_CREATED"})
    return Response(status_code=204)

#======================================DEVICES========================================

@router.get("/devices", tags=["Devices"])
def list_devices(request: Request, query: Annotated[DeviceQuery, Query()]):
    return {"data": request.app.state.services.devices.list(query.pagination())}


@router.post("/devices", status_code=201, tags=["Devices"], dependencies=[Depends(require_super_admin)])
def create_device(request: Request, body: DeviceCreate):
    return {"data": request.app.state.services.devices.create(body.payload())}


@router.get("/devices/{record_id}", tags=["Devices"])
def get_device(record_id: UUID, request: Request):
    return {"data": request.app.state.services.devices.get(str(record_id))}


@router.patch("/devices/{record_id}", tags=["Devices"], dependencies=[Depends(require_super_admin)])
def update_device(record_id: UUID, request: Request, body: DevicePatch):
    return {"data": request.app.state.services.devices.update(str(record_id), body.payload())}


@router.delete("/devices/{record_id}", status_code=204, tags=["Devices"], dependencies=[Depends(require_super_admin)])
async def delete_device(record_id: UUID, request: Request):
    services = request.app.state.services
    device = services.devices.get(str(record_id))
    services.devices.remove(str(record_id))
    services.deletion_history.record(
        entity_type="device",
        entity_id=str(record_id),
        title=f"[{device.get('device_code', '')}] {device.get('name', '')}".strip(),
        reason="Xóa thiết bị thủ công",
        deleted_by=_actor_label(request),
        snapshot=device,
    )
    await ws_manager.broadcast_to_portal({"event": "DELETION_HISTORY_CREATED"})
    return Response(status_code=204)


@router.get("/users/{record_id}/face-embedding", tags=["Face Embeddings"])
def get_embedding(record_id: UUID, request: Request):
    return {"data": request.app.state.services.embeddings.get(str(record_id))}


@router.put("/users/{record_id}/face-embedding", tags=["Face Embeddings"], dependencies=[Depends(require_add_embedding_or_admin)])
async def save_embedding(record_id: UUID, request: Request, body: FaceEmbeddingPut):
    services = request.app.state.services
    saved, finalized_sessions = services.embeddings.save_and_finalize(
        str(record_id),
        body.payload(),
        deleted_by=_actor_label(request),
    )
    for sess in finalized_sessions:
        await ws_manager.broadcast_to_portal({
            "event": "SESSION_FINALIZED",
            "session": sess,
        })
        if sess.get("device_id"):
            await ws_manager.send_to_device(str(sess["device_id"]), {
                "event": "SESSION_FINALIZED",
                "session": sess,
            })
    if finalized_sessions:
        await ws_manager.broadcast_to_portal({"event": "DELETION_HISTORY_CREATED"})
    return {"data": saved}


@router.delete("/users/{record_id}/face-embedding", status_code=204, tags=["Face Embeddings"], dependencies=[Depends(require_super_admin)])
def delete_embedding(record_id: UUID, request: Request):
    request.app.state.services.embeddings.remove(str(record_id))
    return Response(status_code=204)


@router.get("/registration-sessions", tags=["Registration Sessions"])
def list_sessions(request: Request, query: Annotated[SessionQuery, Query()]):
    return {"data": request.app.state.services.sessions.list(query.pagination())}


@router.post("/registration-sessions", status_code=201, tags=["Registration Sessions"], dependencies=[Depends(require_permission("sessions:create"))])
async def create_session(request: Request, body: SessionCreate):
    created = request.app.state.services.sessions.create(body.payload())
    await ws_manager.send_to_device(str(body.device_id), {
        "event": "NEW_REGISTRATION_SESSION",
        "session": created,
    })
    await ws_manager.broadcast_to_portal({
        "event": "SESSION_CREATED",
        "session": created,
    })
    return {"data": created}


@router.get("/registration-sessions/{record_id}", tags=["Registration Sessions"])
def get_session(record_id: UUID, request: Request):
    return {"data": request.app.state.services.sessions.get(str(record_id))}


@router.patch("/registration-sessions/{record_id}", tags=["Registration Sessions"], dependencies=[Depends(require_super_admin)])
async def update_session(record_id: UUID, request: Request, body: SessionPatch):
    updated = request.app.state.services.sessions.update(str(record_id), body.payload())
    await ws_manager.broadcast_to_portal({
        "event": "SESSION_FINALIZED",
        "session": updated,
    })
    return {"data": updated}


@router.delete("/registration-sessions/{record_id}", status_code=204, tags=["Registration Sessions"], dependencies=[Depends(require_super_admin)])
async def delete_session(record_id: UUID, request: Request):
    services = request.app.state.services
    sess = services.sessions.get(str(record_id))
    services.sessions.remove(str(record_id))
    title = f"Phiên {str(record_id)[:8]}"
    try:
        user = services.users.get(str(sess.get("user_id")))
        title = f"[{user.get('user_code', '')}] {user.get('full_name', '')}".strip()
    except Exception:
        pass
    services.deletion_history.record(
        entity_type="session",
        entity_id=str(record_id),
        title=title,
        reason="Xóa phiên đăng ký thủ công",
        deleted_by=_actor_label(request),
        snapshot=sess,
    )
    await ws_manager.broadcast_to_portal({"event": "DELETION_HISTORY_CREATED"})
    return Response(status_code=204)


@router.get("/access-logs", tags=["Access Logs"])
def list_logs(request: Request, query: Annotated[AccessLogQuery, Query()]):
    return {"data": request.app.state.services.logs.list(query.pagination())}


@router.delete("/access-logs", tags=["Access Logs"], dependencies=[Depends(require_super_admin)])
async def delete_logs(request: Request, query: Annotated[AccessLogDeleteQuery, Query()]):
    services = request.app.state.services
    actor = _actor_label(request)
    raw_result = services.logs.delete_by_range(query.payload(), deleted_by=actor)
    deleted_rows = raw_result.get("deleted_rows", [])
    deleted_count = raw_result.get("deleted_count", 0)

    if deleted_count > 0:
        if deleted_count <= 50:
            user_cache = {}
            for row in deleted_rows:
                uid = row.get("user_id")
                title = "Khách (Không nhận diện)"
                if uid:
                    if uid not in user_cache:
                        try:
                            u = services.users.get(str(uid))
                            user_cache[uid] = f"[{u.get('user_code', '')}] {u.get('full_name', '')}".strip()
                        except Exception:
                            user_cache[uid] = str(uid)
                    title = user_cache[uid]
                services.deletion_history.record(
                    entity_type="access_log",
                    entity_id=str(row.get("id")),
                    title=f"{title} · {row.get('result', '')}",
                    reason=f"Xóa lịch sử truy cập ({raw_result['start_time']} → {raw_result['end_time']})",
                    deleted_by=actor,
                    snapshot=row,
                )
        else:
            services.deletion_history.record(
                entity_type="access_log",
                entity_id=f"bulk-{raw_result['start_time']}",
                title=f"Xóa hàng loạt {deleted_count} lượt truy cập",
                reason=f"Xóa theo khoảng thời gian ({raw_result['start_time']} → {raw_result['end_time']})",
                deleted_by=actor,
                snapshot={
                    "deleted_count": deleted_count,
                    "start_time": raw_result["start_time"],
                    "end_time": raw_result["end_time"],
                    "sample_logs": deleted_rows[:20],
                },
            )
        await ws_manager.broadcast_to_portal({"event": "DELETION_HISTORY_CREATED"})

    result = {
        "deleted_count": deleted_count,
        "start_time": raw_result["start_time"],
        "end_time": raw_result["end_time"],
    }
    await ws_manager.broadcast_to_portal({
        "event": "LOGS_DELETED",
        **result,
    })
    return {"data": result}


#===================================DELETION HISTORY==================================

@router.get("/deletion-history", tags=["Deletion History"])
def list_deletion_history(request: Request, query: Annotated[DeletionHistoryQuery, Query()]):
    return {"data": request.app.state.services.deletion_history.list(query.pagination())}


@router.delete("/deletion-history", tags=["Deletion History"], dependencies=[Depends(require_super_admin)])
async def clear_deletion_history(request: Request):
    res = request.app.state.services.deletion_history.clear()
    await ws_manager.broadcast_to_portal({"event": "DELETION_HISTORY_CREATED"})
    return {"data": res}


@router.post("/access-logs", status_code=201, tags=["Access Logs"], dependencies=[Depends(require_super_admin)])
async def create_log(request: Request, response: Response, body: AccessLogCreate):
    data, created = request.app.state.services.logs.create(body.payload())
    response.status_code = 201 if created else 200
    if created:
        await ws_manager.broadcast_to_portal({
            "event": "NEW_ACCESS_LOG",
            "log": data,
        })
    return {"data": data}


@router.get("/access-logs/{record_id}", tags=["Access Logs"])
def get_log(record_id: UUID, request: Request):
    return {"data": request.app.state.services.logs.get(str(record_id))}


#======================================WEBSOCKET====================================

@ws_router.websocket("/ws/devices/{device_id}")
async def ws_device_endpoint(websocket: WebSocket, device_id: str):
    await ws_manager.connect_device(device_id, websocket)
    try:
        while True:
            text = await websocket.receive_text()
            try:
                msg = json.loads(text)
                if msg.get("event") == "PING":
                    await websocket.send_text(json.dumps({"event": "PONG"}))
            except Exception:
                pass
    except WebSocketDisconnect:
        ws_manager.disconnect_device(device_id, websocket)


@ws_router.websocket("/ws/portal")
async def ws_portal_endpoint(websocket: WebSocket):
    await ws_manager.connect_portal(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect_portal(websocket)

