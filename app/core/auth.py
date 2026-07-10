"""
Auth contract — interface only.

Replace get_current_user with your JWT/OAuth/session logic.
Return a CurrentUser (or subclass) from your implementation.
The template does not ship auth. This is intentional.

Consuming apps must implement these before using auth-protected routes.
"""

from pydantic import BaseModel


class CurrentUser(BaseModel):
    """Minimal user schema. Extend as needed."""

    id: str
    email: str
    roles: list[str] = []


def get_current_user() -> CurrentUser:
    """
    FastAPI dependency for authenticated user.

    Replace this with your JWT/OAuth/session logic.
    By default raises NotImplementedError.
    """
    raise NotImplementedError(
        "Auth not configured. Implement get_current_user in app/core/auth.py."
    )


def require_roles(*roles: str):
    """
    Dependency factory for role-based guards.

    Usage: Depends(require_roles("admin", "editor"))
    By default raises NotImplementedError.
    """

    def _require_roles():
        raise NotImplementedError(
            "Auth not configured. Implement require_roles in app/core/auth.py."
        )

    return _require_roles
