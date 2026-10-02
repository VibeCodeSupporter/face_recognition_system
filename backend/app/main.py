import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from app.config import BACKEND_ROOT, Settings, load_settings
from app.controllers import router
from app.dto.common import ErrorResponse
from app.errors import AppError
from app.infrastructure.database import Database
from app.middleware import RequestGuard
from app.repositories import Repositories
from app.services import Services


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        database = Database(settings)
        try:
            await run_in_threadpool(database.check)
            application.state.database = database
            application.state.services = Services(Repositories(database))
            yield
        finally:
            database.close()

    application = FastAPI(title="FaceAccess Backend API", version="1.0.0", lifespan=lifespan, redirect_slashes=False)
    application.add_middleware(RequestGuard, api_key=settings.api_key)
    application.include_router(router, responses={
        400: {"model": ErrorResponse, "description": "Invalid JSON, body, path or query parameters.",
              "content": {"application/json": {"example": {"error": {
                  "code": "VALIDATION_ERROR", "message": "Request validation failed.",
                  "request_id": "00000000-0000-4000-8000-000000000000",
                  "details": [{"path": "body.user_code", "message": "Field required"}],
              }}}}},
        401: {"model": ErrorResponse, "description": "Missing or invalid backend x-api-key."},
        404: {"model": ErrorResponse, "description": "The requested record or route was not found."},
        409: {"model": ErrorResponse, "description": "Duplicate record, reference conflict or invalid state."},
        413: {"model": ErrorResponse, "description": "Request body exceeds 128 KB."},
        422: {"model": ErrorResponse, "description": "Database constraint or database value violation.",
              "content": {"application/json": {"example": {"error": {
                  "code": "CONSTRAINT_VIOLATION", "message": "The record violates a database constraint.",
                  "request_id": "00000000-0000-4000-8000-000000000000",
              }}}}},
        500: {"model": ErrorResponse, "description": "Unexpected server error."},
        503: {"model": ErrorResponse, "description": "Database unavailable."},
    })

    portal_root = BACKEND_ROOT.parent / "web_test_api"
    if portal_root.is_dir():
        application.mount("/portal", StaticFiles(directory=portal_root, html=True), name="portal")

    def error_response(request: Request, status: int, code: str, message: str, details=None):
        request_id = getattr(request.state, "request_id", "")
        error = {"code": code, "message": message, "request_id": request_id}
        if details is not None:
            error["details"] = details
        return JSONResponse({"error": error}, status_code=status, headers={
            "X-Request-Id": request_id, "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
        })

    @application.exception_handler(AppError)
    async def app_error(request: Request, error: AppError):
        return error_response(request, error.status, error.code, error.message)

    @application.exception_handler(RequestValidationError)
    async def validation_error(request: Request, error: RequestValidationError):
        invalid_json = any(item["type"] == "json_invalid" for item in error.errors())
        details = [{"path": ".".join(map(str, item["loc"])), "message": item["msg"]} for item in error.errors()]
        return error_response(request, 400, "INVALID_JSON" if invalid_json else "VALIDATION_ERROR", "Request validation failed.", details)

    @application.exception_handler(HTTPException)
    async def http_error(request: Request, error: HTTPException):
        status = 404 if error.status_code in {404, 405} else error.status_code
        return error_response(request, status, "ROUTE_NOT_FOUND" if status == 404 else "HTTP_ERROR", "The requested API route does not exist." if status == 404 else "The HTTP request was rejected.")

    @application.exception_handler(Exception)
    async def unexpected_error(request: Request, _error: Exception):
        logging.getLogger("faceaccess").error("Unhandled request failure: %s", getattr(request.state, "request_id", ""))
        return error_response(request, 500, "INTERNAL_ERROR", "The request could not be completed.")

    return application
