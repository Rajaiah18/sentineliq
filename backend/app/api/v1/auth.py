"""
SentinelIQ Authentication API Router
"""
from fastapi import APIRouter, HTTPException, status, Response, Request
from pydantic import BaseModel
from backend.app.security.auth import authenticate_user, create_access_token
from backend.app.security.permissions import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    username: str
    role: str
    full_name: str


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, response: Response):
    user = authenticate_user(payload.username, payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials. Verify username and password."
        )

    token = create_access_token(data={"sub": user["username"], "role": user["role"]})

    # Set secure HTTP-only cookie for server-rendered UI
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=False  # Allow local HTTP in dev
    )

    return LoginResponse(
        access_token=token,
        user_id=user["user_id"],
        username=user["username"],
        role=user["role"],
        full_name=user["full_name"]
    )


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("access_token")
    return {"status": "success", "message": "Logged out successfully."}


@router.get("/me")
def get_profile(request: Request):
    user = get_current_user(request)
    return {
        "user_id": user["user_id"],
        "username": user["username"],
        "email": user["email"],
        "role": user["role"],
        "full_name": user["full_name"]
    }
