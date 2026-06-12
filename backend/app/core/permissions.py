from enum import Enum
from typing import List
from fastapi import Depends, HTTPException, status
from app.dependencies import get_current_user
from app.schemas.auth import UserRead


class UserRole(str, Enum):
    """
    5-tier RBAC for Clavra ProdPilot™.
    Hierarchy: admin > manager > supervisor > qc_inspector > viewer
    """
    ADMIN        = "admin"
    MANAGER      = "manager"
    SUPERVISOR   = "supervisor"
    QC_INSPECTOR = "qc_inspector"
    VIEWER       = "viewer"


# Role hierarchy — higher index = more permissions
ROLE_HIERARCHY = [
    UserRole.VIEWER,
    UserRole.QC_INSPECTOR,
    UserRole.SUPERVISOR,
    UserRole.MANAGER,
    UserRole.ADMIN,
]


def role_level(role: str) -> int:
    """Return numeric level of a role (higher = more powerful)."""
    try:
        return ROLE_HIERARCHY.index(UserRole(role))
    except (ValueError, KeyError):
        return -1


def require_role(*allowed_roles: UserRole):
    """
    FastAPI dependency factory for role-based access control.

    Usage:
        @router.get("/admin-only")
        async def admin_route(user = Depends(require_role(UserRole.ADMIN))):
            ...

        @router.get("/manager-or-above")
        async def mgr_route(user = Depends(require_role(UserRole.ADMIN, UserRole.MANAGER))):
            ...
    """
    async def check_role(current_user: UserRead = Depends(get_current_user)):
        if current_user.role not in [r.value for r in allowed_roles]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {[r.value for r in allowed_roles]}"
            )
        return current_user
    return check_role


def require_min_role(min_role: UserRole):
    """
    Dependency that allows the specified role AND all higher roles.

    Usage:
        @router.get("/supervisor-and-above")
        async def route(user = Depends(require_min_role(UserRole.SUPERVISOR))):
            ...
    """
    async def check_min_role(current_user: UserRead = Depends(get_current_user)):
        if role_level(current_user.role) < role_level(min_role.value):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Minimum required role: {min_role.value}"
            )
        return current_user
    return check_min_role
