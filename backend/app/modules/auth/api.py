from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_runtime, get_session
from app.core.security import client_key
from app.modules.auth.schemas import AuthStatus, LoginRequest, OwnerView
from app.modules.auth.service import AuthService, Tokens, unauthorized
from app.shared.identity import Principal

router = APIRouter(prefix="/auth", tags=["authentication"])
Session = Annotated[AsyncSession, Depends(get_session)]


def service(request: Request, session: Session) -> AuthService:
    return AuthService(session, get_runtime(request).settings)


Service = Annotated[AuthService, Depends(service)]


async def require_owner(request: Request, auth: Service) -> OwnerView:
    token = request.cookies.get("__Host-jh_access")
    if not token:
        raise unauthorized()
    owner = await auth.current_owner(token)
    request.state.principal = Principal(owner.id)
    return owner


def set_cookies(response: Response, tokens: Tokens, request: Request) -> None:
    settings = get_runtime(request).settings
    response.set_cookie(
        "__Host-jh_access",
        tokens.access,
        max_age=settings.access_minutes * 60,
        secure=True,
        httponly=True,
        samesite="strict",
        path="/",
    )
    response.set_cookie(
        "__Host-jh_refresh",
        tokens.refresh,
        max_age=settings.refresh_days * 86400,
        secure=True,
        httponly=True,
        samesite="strict",
        path="/",
    )
    response.headers["Cache-Control"] = "no-store"


@router.post("/login", response_model=AuthStatus)
async def login(
    body: LoginRequest, request: Request, response: Response, auth: Service
) -> AuthStatus:
    settings = get_runtime(request).settings
    address = request.client.host if request.client else "unknown"
    key = client_key(address, settings.jwt_secret.get_secret_value())
    tokens = await auth.login(body.email, body.password.get_secret_value(), key)
    set_cookies(response, tokens, request)
    return AuthStatus(owner=tokens.owner)


@router.post("/refresh", response_model=AuthStatus)
async def refresh(request: Request, response: Response, auth: Service) -> AuthStatus:
    raw = request.cookies.get("__Host-jh_refresh")
    if not raw or len(raw) > 256:
        raise unauthorized()
    tokens = await auth.rotate(raw)
    set_cookies(response, tokens, request)
    return AuthStatus(owner=tokens.owner)


@router.post("/logout", status_code=204)
async def logout(request: Request, auth: Service) -> Response:
    raw = request.cookies.get("__Host-jh_refresh")
    if raw and len(raw) <= 256:
        await auth.logout(raw)
    response = Response(status_code=204, headers={"Cache-Control": "no-store"})
    for name in ("__Host-jh_access", "__Host-jh_refresh"):
        response.delete_cookie(name, secure=True, httponly=True, samesite="strict", path="/")
    return response


@router.get("/me", response_model=OwnerView)
async def me(owner: Annotated[OwnerView, Depends(require_owner)]) -> OwnerView:
    return owner
