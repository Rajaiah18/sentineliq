"""
SentinelIQ Tests: Role-Based Access Control & Security Policies
"""
import pytest
from fastapi import HTTPException
from backend.app.security.auth import (
    hash_password, verify_password, create_access_token, decode_access_token, authenticate_user, get_demo_users
)
from backend.app.security.permissions import require_roles


def test_password_hashing():
    pw = "SuperSecurePassword2026!"
    h = hash_password(pw)
    assert h != pw
    assert verify_password(pw, h) is True
    assert verify_password("WrongPassword!", h) is False


def test_jwt_token_generation_and_verification():
    token = create_access_token({"sub": "admin", "role": "ADMIN"})
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "admin"
    assert payload["role"] == "ADMIN"


def test_role_enforcement():
    admin_checker = require_roles(["ADMIN"])
    analyst_checker = require_roles(["ADMIN", "ANALYST"])

    admin_user = get_demo_users()["admin"]
    analyst_user = get_demo_users()["analyst"]
    readonly_user = get_demo_users()["readonly"]

    # Admin allowed for both
    assert admin_checker(admin_user)["role"] == "ADMIN"
    assert analyst_checker(admin_user)["role"] == "ADMIN"

    # Analyst allowed for analyst checker
    assert analyst_checker(analyst_user)["role"] == "ANALYST"

    # Analyst forbidden for admin checker
    with pytest.raises(HTTPException) as exc1:
        admin_checker(analyst_user)
    assert exc1.value.status_code == 403

    # Readonly forbidden for admin and analyst
    with pytest.raises(HTTPException) as exc2:
        admin_checker(readonly_user)
    assert exc2.value.status_code == 403
