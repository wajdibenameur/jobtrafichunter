from fastapi import Request

from app.core.errors import AppError
from app.shared.identity import Principal


def require_identity(request: Request) -> Principal:
    principal = getattr(request.state, "principal", None)
    if not isinstance(principal, Principal):
        raise AppError("UNAUTHENTICATED", "Authentication required", 401)
    return principal
