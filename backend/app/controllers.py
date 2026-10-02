from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Request, Response, Security
from fastapi.security import APIKeyHeader

from app.dto.access_logs import AccessLogCreate, AccessLogQuery
from app.dto.devices import DeviceCreate, DevicePatch, DeviceQuery
from app.dto.face_embeddings import FaceEmbeddingPut
from app.dto.registration_sessions import SessionCreate, SessionPatch, SessionQuery
from app.dto.users import UserCreate, UserPatch, UserQuery

router = APIRouter(prefix="/api/v1", dependencies=[Security(APIKeyHeader(name="x-api-key", auto_error=False))])


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
 

@router.post("/users", status_code=201, tags=["Users"])
def create_user(request: Request, body: UserCreate):
    return {"data": request.app.state.services.users.create(body.payload())}


@router.get("/users/{record_id}", tags=["Users"])
def get_user(record_id: UUID, request: Request):
    return {"data": request.app.state.services.users.get(str(record_id))}


@router.patch("/users/{record_id}", tags=["Users"])
def update_user(record_id: UUID, request: Request, body: UserPatch):
    return {"data": request.app.state.services.users.update(str(record_id), body.payload())}


@router.delete("/users/{record_id}", status_code=204, tags=["Users"])
def delete_user(record_id: UUID, request: Request):
    request.app.state.services.users.remove(str(record_id))
    return Response(status_code=204)

#======================================DEVICES========================================

@router.get("/devices", tags=["Devices"])
def list_devices(request: Request, query: Annotated[DeviceQuery, Query()]):
    return {"data": request.app.state.services.devices.list(query.pagination())}


@router.post("/devices", status_code=201, tags=["Devices"])
def create_device(request: Request, body: DeviceCreate):
    return {"data": request.app.state.services.devices.create(body.payload())}


@router.get("/devices/{record_id}", tags=["Devices"])
def get_device(record_id: UUID, request: Request):
    return {"data": request.app.state.services.devices.get(str(record_id))}


@router.patch("/devices/{record_id}", tags=["Devices"])
def update_device(record_id: UUID, request: Request, body: DevicePatch):
    return {"data": request.app.state.services.devices.update(str(record_id), body.payload())}


@router.delete("/devices/{record_id}", status_code=204, tags=["Devices"])
def delete_device(record_id: UUID, request: Request):
    request.app.state.services.devices.remove(str(record_id))
    return Response(status_code=204)


@router.get("/users/{record_id}/face-embedding", tags=["Face Embeddings"])
def get_embedding(record_id: UUID, request: Request):
    return {"data": request.app.state.services.embeddings.get(str(record_id))}


@router.put("/users/{record_id}/face-embedding", tags=["Face Embeddings"])
def save_embedding(record_id: UUID, request: Request, body: FaceEmbeddingPut):
    return {"data": request.app.state.services.embeddings.save(str(record_id), body.payload())}


@router.delete("/users/{record_id}/face-embedding", status_code=204, tags=["Face Embeddings"])
def delete_embedding(record_id: UUID, request: Request):
    request.app.state.services.embeddings.remove(str(record_id))
    return Response(status_code=204)


@router.get("/registration-sessions", tags=["Registration Sessions"])
def list_sessions(request: Request, query: Annotated[SessionQuery, Query()]):
    return {"data": request.app.state.services.sessions.list(query.pagination())}


@router.post("/registration-sessions", status_code=201, tags=["Registration Sessions"])
def create_session(request: Request, body: SessionCreate):
    return {"data": request.app.state.services.sessions.create(body.payload())}


@router.get("/registration-sessions/{record_id}", tags=["Registration Sessions"])
def get_session(record_id: UUID, request: Request):
    return {"data": request.app.state.services.sessions.get(str(record_id))}


@router.patch("/registration-sessions/{record_id}", tags=["Registration Sessions"])
def update_session(record_id: UUID, request: Request, body: SessionPatch):
    return {"data": request.app.state.services.sessions.update(str(record_id), body.payload())}


@router.delete("/registration-sessions/{record_id}", status_code=204, tags=["Registration Sessions"])
def delete_session(record_id: UUID, request: Request):
    request.app.state.services.sessions.remove(str(record_id))
    return Response(status_code=204)


@router.get("/access-logs", tags=["Access Logs"])
def list_logs(request: Request, query: Annotated[AccessLogQuery, Query()]):
    return {"data": request.app.state.services.logs.list(query.pagination())}


@router.post("/access-logs", status_code=201, tags=["Access Logs"])
def create_log(request: Request, response: Response, body: AccessLogCreate):
    data, created = request.app.state.services.logs.create(body.payload())
    response.status_code = 201 if created else 200
    return {"data": data}


@router.get("/access-logs/{record_id}", tags=["Access Logs"])
def get_log(record_id: UUID, request: Request):
    return {"data": request.app.state.services.logs.get(str(record_id))}
