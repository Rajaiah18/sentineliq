"""
SentinelIQ Centralized Role-Based Access Control (RBAC) & Permission Policy
Enforces authorization server-side for both API and server-rendered HTML routes.
Roles: ADMIN, ANALYST, COMPLIANCE_REVIEWER, READ_ONLY.
"""
from typing import List, Dict, Any, Optional, Set
from fastapi import Depends, HTTPException, status, Header, Cookie, Request
from backend.app.security.auth import decode_access_token

VALID_ROLES: Set[str] = {"ADMIN", "ANALYST", "COMPLIANCE_REVIEWER", "READ_ONLY"}

def normalize_role(role: Optional[str]) -> str:
    """Normalize role string. Fails closed to READ_ONLY if missing or invalid."""
    if not role:
        return "READ_ONLY"
    role_norm = str(role).strip().upper()
    return role_norm if role_norm in VALID_ROLES else "READ_ONLY"


ROLE_PERMISSIONS: Dict[str, Set[str]] = {
    "ADMIN": {
        "view:dashboard",
        "view:admin_dashboard",
        "view:transactions",
        "view:customers",
        "view:accounts",
        "view:alerts",
        "edit:alerts",
        "view:cases",
        "create:cases",
        "edit:cases",
        "disposition:cases",
        "view:rules",
        "edit:rules",
        "view:validation",
        "run:validation",
        "view:evaluation",
        "run:evaluation",
        "view:generator",
        "run:generator",
        "view:audit",
        "manage:users",
        "manage:system",
        "view:reports",
        "view:workspace"
    },
    "ANALYST": {
        "view:dashboard",
        "view:analyst_dashboard",
        "view:transactions",
        "view:customers",
        "view:accounts",
        "view:alerts",
        "edit:alerts",
        "view:cases",
        "create:cases",
        "edit:cases",
        "view:workspace",
        "test:rules"
    },
    "COMPLIANCE_REVIEWER": {
        "view:dashboard",
        "view:compliance_dashboard",
        "view:alerts",
        "view:cases",
        "disposition:cases",
        "view:audit",
        "view:validation",
        "run:validation",
        "view:evaluation",
        "run:evaluation",
        "view:reports"
    },
    "READ_ONLY": {
        "view:dashboard",
        "view:readonly_dashboard",
        "view:transactions",
        "view:customers",
        "view:accounts",
        "view:alerts",
        "view:cases",
        "view:reports"
    }
}


def has_permission(role: str, permission: str) -> bool:
    """Check if given role has specified permission."""
    norm = normalize_role(role)
    perms = ROLE_PERMISSIONS.get(norm, set())
    return permission in perms


def get_navigation_for_role(role: str) -> List[Dict[str, str]]:
    """
    Return exact navigation items for the authenticated role.
    Target design specified in challenge Section 3.
    """
    norm = normalize_role(role)
    if norm == "ADMIN":
        return [
            {"id": "dashboard", "name": "Dashboard", "url": "/dashboard"},
            {"id": "transactions", "name": "Transactions", "url": "/transactions"},
            {"id": "customers", "name": "Customers", "url": "/customers"},
            {"id": "accounts", "name": "Accounts", "url": "/accounts"},
            {"id": "alerts", "name": "Alerts", "url": "/alerts"},
            {"id": "cases", "name": "Cases", "url": "/cases"},
            {"id": "rules", "name": "Rules", "url": "/rules"},
            {"id": "validation", "name": "Data Quality", "url": "/validation"},
            {"id": "evaluation", "name": "Evaluation", "url": "/evaluation"},
            {"id": "generator", "name": "Exports & Generation", "url": "/generator"},
            {"id": "audit", "name": "Audit Log", "url": "/audit"},
            {"id": "users", "name": "User Management", "url": "/users"},
            {"id": "settings", "name": "System Settings", "url": "/settings"}
        ]
    elif norm == "ANALYST":
        return [
            {"id": "dashboard", "name": "My Dashboard", "url": "/dashboard"},
            {"id": "transactions", "name": "Transactions", "url": "/transactions"},
            {"id": "customers", "name": "Customers", "url": "/customers"},
            {"id": "accounts", "name": "Accounts", "url": "/accounts"},
            {"id": "alerts", "name": "Alerts", "url": "/alerts"},
            {"id": "cases", "name": "My Cases", "url": "/cases?filter=my_cases"},
            {"id": "workspace", "name": "Investigation Workspace", "url": "/cases/workspace"}
        ]
    elif norm == "COMPLIANCE_REVIEWER":
        return [
            {"id": "dashboard", "name": "Compliance Dashboard", "url": "/dashboard"},
            {"id": "alerts", "name": "Alerts", "url": "/alerts"},
            {"id": "cases", "name": "Cases for Review", "url": "/cases?status=PENDING_REVIEW"},
            {"id": "audit", "name": "Audit Log", "url": "/audit"},
            {"id": "validation", "name": "Data Quality", "url": "/validation"},
            {"id": "evaluation", "name": "Evaluation", "url": "/evaluation"},
            {"id": "reports", "name": "Reports", "url": "/reports"}
        ]
    else:  # READ_ONLY
        return [
            {"id": "dashboard", "name": "Overview Dashboard", "url": "/dashboard"},
            {"id": "transactions", "name": "Transactions", "url": "/transactions"},
            {"id": "customers", "name": "Customers", "url": "/customers"},
            {"id": "accounts", "name": "Accounts", "url": "/accounts"},
            {"id": "alerts", "name": "Alerts", "url": "/alerts"},
            {"id": "cases", "name": "Read-Only Cases", "url": "/cases"},
            {"id": "reports", "name": "Reports", "url": "/reports"}
        ]


def get_current_user(
    request: Request,
    authorization: Optional[str] = Header(None),
    access_token: Optional[str] = Cookie(None)
) -> Dict[str, Any]:
    """
    Extract and validate current authenticated user from Authorization Bearer header
    or session cookie 'access_token'.
    Loads authoritative user record from repository to guarantee real-time role state.
    """
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
    elif access_token:
        token = access_token
    elif "access_token" in request.cookies:
        token = request.cookies["access_token"]

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide a valid Bearer token or login.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    username = payload.get("sub")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token claims: subject missing."
        )

    from backend.app.database.repository import repo
    user = repo.get_user_by_username(username)
    if not user or not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user no longer active or exists."
        )

    # Normalize user's role
    user["role"] = normalize_role(user.get("role"))
    return user


def require_roles(allowed_roles: List[str]):
    """Role-based authorization dependency factory for API routes."""
    allowed_norm = {normalize_role(r) for r in allowed_roles}
    def role_checker(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        user_role = normalize_role(user.get("role"))
        if user_role not in allowed_norm:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Role '{user_role}' lacks required permissions ({', '.join(sorted(allowed_norm))})."
            )
        return user
    return role_checker


def require_permission(permission: str):
    """Fine-grained permission dependency factory for API routes."""
    def permission_checker(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        user_role = normalize_role(user.get("role"))
        if not has_permission(user_role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Role '{user_role}' lacks required permission '{permission}'."
            )
        return user
    return permission_checker


# Convenient Pre-configured Role Dependencies for API routes
RequireAdmin = Depends(require_roles(["ADMIN"]))
RequireAnalyst = Depends(require_roles(["ADMIN", "ANALYST"]))
RequireCompliance = Depends(require_roles(["ADMIN", "COMPLIANCE_REVIEWER"]))
RequireReadWrite = Depends(require_roles(["ADMIN", "ANALYST", "COMPLIANCE_REVIEWER"]))
RequireAuthenticated = Depends(get_current_user)
