"""Public auth contract; consumers never import auth internals."""

from app.modules.auth.api import require_owner, router
from app.modules.auth.schemas import OwnerView
from app.modules.auth.service import AuthService

__all__ = ["AuthService", "OwnerView", "require_owner", "router"]
