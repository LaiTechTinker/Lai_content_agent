from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.dependencies import get_current_user
from app.core.security import normalize_email
from app.services.auth_service import (
    authenticate_user,
    issue_tokens,
    register_user,
    revoke_refresh_token,
    rotate_refresh_token,
)


router = APIRouter(prefix="/auth", tags=["authentication"])


class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=20)


class UserResponse(BaseModel):
    id: int
    name: str | None
    email: str
    is_active: bool
    created_at: str | None
    updated_at: str | None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int


@router.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)
def register(request: RegisterRequest):
    try:
        user = register_user(request.name, normalize_email(request.email), request.password)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"user": user}


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest):
    user = authenticate_user(request.email, request.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid email or password.", headers={"WWW-Authenticate": "Bearer"})
    return issue_tokens(user["id"])


@router.post("/refresh", response_model=TokenResponse)
def refresh(request: RefreshRequest):
    tokens = rotate_refresh_token(request.refresh_token)
    if tokens is None:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token.")
    return tokens


@router.post("/logout")
def logout(request: RefreshRequest):
    revoke_refresh_token(request.refresh_token)
    return {"logged_out": True}


@router.get("/me", response_model=UserResponse)
def me(current_user: dict = Depends(get_current_user)):
    return current_user