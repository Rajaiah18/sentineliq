"""
SentinelIQ Authentication & Security Utilities
Native bcrypt password hashing, JWT token encoding/decoding, and demo user provisioning.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import bcrypt
from jose import JWTError, jwt
from backend.app.config import settings


def hash_password(password: str) -> str:
    """Hash plaintext password with native bcrypt."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plaintext password against bcrypt hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Generate signed JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate signed JWT token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None


_demo_users_cache = None

def get_demo_users():
    global _demo_users_cache
    if _demo_users_cache is None:
        _demo_users_cache = {
            "admin": {
                "user_id": "USR-ADMIN-01",
                "username": "admin",
                "email": "admin@sentineliq.internal",
                "hashed_password": hash_password(settings.DEMO_ADMIN_PASSWORD),
                "role": "ADMIN",
                "full_name": "Chief Risk Officer",
                "is_active": True
            },
            "analyst": {
                "user_id": "USR-ANALYST-01",
                "username": "analyst",
                "email": "analyst@sentineliq.internal",
                "hashed_password": hash_password(settings.DEMO_ANALYST_PASSWORD),
                "role": "ANALYST",
                "full_name": "Lead Financial Crime Investigator",
                "is_active": True
            },
            "compliance": {
                "user_id": "USR-COMPLIANCE-01",
                "username": "compliance",
                "email": "compliance@sentineliq.internal",
                "hashed_password": hash_password(settings.DEMO_COMPLIANCE_PASSWORD),
                "role": "COMPLIANCE_REVIEWER",
                "full_name": "Senior Regulatory Compliance Officer",
                "is_active": True
            },
            "readonly": {
                "user_id": "USR-READONLY-01",
                "username": "readonly",
                "email": "audit@sentineliq.internal",
                "hashed_password": hash_password(settings.DEMO_READONLY_PASSWORD),
                "role": "READ_ONLY",
                "full_name": "External Auditor",
                "is_active": True
            }
        }
    return _demo_users_cache


def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """Authenticate user credentials honestly."""
    if not settings.ENABLE_DEMO_USERS:
        return None
    users = get_demo_users()
    user = users.get(username.lower())
    if not user:
        return None
    if not verify_password(password, user["hashed_password"]):
        return None
    return user
