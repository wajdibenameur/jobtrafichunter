import base64
import hashlib
import logging
import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from app.core.body_limit import BodyLimitMiddleware
from app.core.db import get_runtime, make_runtime
from app.core.errors import AppError
from app.core.logging import configure_logging, correlation_id
from app.core.settings import Settings
from app.modules.ai import LocalDocumentInspector
from app.modules.auth import OwnerView, require_owner
from app.modules.auth import router as auth_router
from app.modules.cv import router as cv_router
from app.modules.listings import router as listings_router
from app.modules.profile import router as profile_router
from app.modules.search import router as search_router
from app.modules.sources import SourceService
from app.modules.sources import router as source_router
from app.shared.source_reference import SourceReference

logger = logging.getLogger("jobhunter.api")


class Health(BaseModel):
    status: str
    database: str


def create_app(settings: Settings | None = None) -> FastAPI:
    runtime = make_runtime(settings or Settings())
    configure_logging()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        try:
            async with runtime.engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
            logger.info("api_started")
            yield
        finally:
            await runtime.engine.dispose()

    app = FastAPI(
        title="JobHunter AI",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
    )
    app.state.runtime = runtime
    app.state.cv_inspector = LocalDocumentInspector(runtime.settings.cv_sandbox_path)
    app.state.cv_probe = app.state.cv_inspector.verify

    async def source_lookup(user_id: UUID, source_id: UUID) -> SourceReference:
        async with runtime.sessions() as session:
            return await SourceService(session).resolve(user_id, source_id)

    app.state.source_lookup = source_lookup
    app.add_middleware(
        CORSMiddleware,
        allow_origins=runtime.settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "X-Correlation-ID", "X-CV-Filename"],
        expose_headers=["X-Correlation-ID"],
    )
    app.add_middleware(BodyLimitMiddleware)

    @app.middleware("http")
    async def security(request: Request, call_next: RequestResponseEndpoint) -> Response:
        try:
            request_id = str(UUID(request.headers.get("X-Correlation-ID", "")))
        except ValueError:
            request_id = str(uuid4())
        context_token = correlation_id.set(request_id)
        try:
            origin = request.headers.get("origin")
            if request.method not in {"GET", "HEAD", "OPTIONS"} and (
                origin not in runtime.settings.allowed_origins
            ):
                response: Response = JSONResponse(
                    {"error": {"code": "ORIGIN_REJECTED", "message": "Trusted origin required"}},
                    status_code=403,
                )
            else:
                response = await call_next(request)
        except Exception:
            logger.error("unhandled_request_error")
            response = JSONResponse(
                {"error": {"code": "INTERNAL_ERROR", "message": "An internal error occurred"}},
                status_code=500,
            )
        finally:
            correlation_id.reset(context_token)
        response.headers.update(
            {
                "X-Correlation-ID": request_id,
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "Referrer-Policy": "no-referrer",
                "Cache-Control": "no-store",
                "Permissions-Policy": "camera=(), microphone=()",
            }
        )
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'none'; frame-ancestors 'none'; base-uri 'none'",
        )
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            {"error": {"code": exc.code, "message": exc.message}},
            status_code=exc.status,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        # Do not expose or log Pydantic's input (may contain passwords/CV text).
        return JSONResponse(
            {"error": {"code": "VALIDATION_ERROR", "message": "Invalid request data"}},
            status_code=422,
        )

    @app.exception_handler(HTTPException)
    async def http_error_handler(request: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(
            {"error": {"code": "HTTP_ERROR", "message": "Request rejected"}},
            status_code=exc.status_code,
            headers=exc.headers,
        )

    @app.get("/health", response_model=Health, tags=["operations"])
    async def health(request: Request) -> JSONResponse:
        try:
            async with get_runtime(request).engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
            return JSONResponse(Health(status="ok", database="ok").model_dump())
        except (SQLAlchemyError, OSError, TimeoutError):
            return JSONResponse(
                Health(status="degraded", database="unavailable").model_dump(),
                status_code=503,
            )

    @app.get("/docs", include_in_schema=False)
    async def docs() -> Response:
        response = get_swagger_ui_html(openapi_url="/openapi.json", title="JobHunter API")
        markup = bytes(response.body).decode()
        scripts = re.findall(r"<script>(.*?)</script>", markup, flags=re.DOTALL)
        hashes = " ".join(
            "'sha256-" + base64.b64encode(hashlib.sha256(script.encode()).digest()).decode() + "'"
            for script in scripts
        )
        response.headers["Content-Security-Policy"] = (
            f"default-src 'none'; script-src https://cdn.jsdelivr.net {hashes}; "
            "style-src https://cdn.jsdelivr.net 'unsafe-inline'; connect-src 'self'; "
            "img-src data: https://fastapi.tiangolo.com; frame-ancestors 'none'; base-uri 'none'"
        )
        return response

    @app.get("/api/account", response_model=OwnerView, tags=["account"])
    async def account(owner: Annotated[OwnerView, Depends(require_owner)]) -> OwnerView:
        return owner

    app.include_router(auth_router, prefix="/api")
    app.include_router(source_router, prefix="/api", dependencies=[Depends(require_owner)])
    app.include_router(cv_router, prefix="/api", dependencies=[Depends(require_owner)])
    app.include_router(profile_router, prefix="/api", dependencies=[Depends(require_owner)])
    app.include_router(listings_router, prefix="/api", dependencies=[Depends(require_owner)])
    app.include_router(search_router, prefix="/api", dependencies=[Depends(require_owner)])
    return app
