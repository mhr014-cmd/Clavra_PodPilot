from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


# ── Request schemas ───────────────────────────────────────────────────────

class RegisterSchema(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    role: Optional[str] = "viewer"
    org_id: Optional[int] = None


class LoginSchema(BaseModel):
    email: EmailStr
    password: str


class RefreshTokenSchema(BaseModel):
    refresh_token: str


# ── Response schemas ──────────────────────────────────────────────────────

class UserRead(BaseModel):
    id: int
    full_name: str
    email: str
    role: str
    org_id: Optional[int] = None
    is_active: bool
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserRead


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MessageResponse(BaseModel):
    message: str
