"""
SentinelIQ Role-Based Access Control & FastAPI Dependencies
Defines logical roles: ADMIN, ANALYST, COMPLIANCE_REVIEWER, READ_ONLY.
Enforces permissions server-side.
"""
from typing import List, Dict, Any, Optional
from fastapi import Depends, HTTPException, status, Header, Cookie, Request
from backend.app.security.auth import decode_access_token, get_demo_users


def get_current_user(
    request: Request,
    authorization: Optional[str] = Header(None),
    access_token: Optional[str] = Cookie(None)
) -> Dict[str, Any]:
    """
    Extract and validate current authenticated user from Authorization Bearer header
    or session cookie 'access_token'.
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
    users = get_demo_users()
    if not username or username not in users:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user no longer active or exists."
        )

    user = users[username]
    return user


def require_roles(allowed_roles: List[str]):
    """Role-based authorization dependency factory."""
    def role_checker(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        user_role = user.get("role", "READ_ONLY")
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Role '{user_role}' lacks required permissions ({', '.join(allowed_roles)})."
            )
        return user
    return role_checker


# Convenient Pre-configured Role Dependencies
RequireAdmin = Depends(require_roles(["ADMIN"]))
RequireAnalyst = Depends(require_roles(["ADMIN", "ANALYST"]))
RequireCompliance = Depends(require_roles(["ADMIN", "ANALYST", "COMPLIANCE_REVIEWER"]))
RequireAuthenticated = Depends(get_current_user)
