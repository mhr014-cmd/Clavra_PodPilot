from fastapi import APIRouter, HTTPException, Depends, Response, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone

from app.dependencies import get_db, get_current_user
from app.models.user import User
from app.models.organization import Organization
from app.core.security import (
    hash_password, verify_password,
    hash_token, verify_token_hash,
    create_access_token, create_refresh_token,
    decode_refresh_token
)
from app.schemas.auth import (
    RegisterSchema, LoginSchema, TokenResponse,
    AccessTokenResponse, MessageResponse, UserRead
)
from app.core.constants import REFRESH_TOKEN_COOKIE

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ── Register ──────────────────────────────────────────────────────────────

@router.post("/register", response_model=MessageResponse, status_code=201)
async def register(payload: RegisterSchema, db: AsyncSession = Depends(get_db)):
    """Register a new user. Creates a default org if org_id not provided."""

    # Check duplicate email
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    # Auto-create org if none provided
    org_id = payload.org_id
    if not org_id:
        import uuid
        base_slug = payload.email.split("@")[0].lower().replace(".", "_")[:40]
        slug = f"{base_slug}_{uuid.uuid4().hex[:6]}"  # ensure uniqueness
        org = Organization(name=f"{payload.full_name}'s Organisation", slug=slug)
        db.add(org)
        await db.flush()
        org_id = org.id

    user = User(
        full_name=payload.full_name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role or "viewer",
        org_id=org_id,
        is_active=True,
    )
    db.add(user)
    await db.commit()

    return {"message": "Registration successful. Please log in."}


# ── Login ─────────────────────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginSchema,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """Authenticate and return access + refresh token pair."""

    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")

    # Create tokens
    token_data = {
        "sub": str(user.id),
        "org_id": user.org_id,
        "role": user.role,
        "email": user.email,
    }
    access_token   = create_access_token(token_data)
    refresh_token  = create_refresh_token(user.id)

    # Store hashed refresh token + last login
    user.refresh_token_hash = hash_token(refresh_token)
    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(user)

    # Set refresh token as httpOnly cookie
    response.set_cookie(
        key=REFRESH_TOKEN_COOKIE,
        value=refresh_token,
        httponly=True,
        secure=False,      # True in production (HTTPS)
        samesite="lax",
        max_age=60 * 60 * 24 * 7  # 7 days
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserRead.model_validate(user)
    )


# ── Refresh ───────────────────────────────────────────────────────────────

@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh_token(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """
    Use the refresh token (from httpOnly cookie or request body)
    to issue a new access token.
    """
    # Try cookie first, then Authorization header body
    token = request.cookies.get(REFRESH_TOKEN_COOKIE)
    if not token:
        body = await request.json()
        token = body.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="Refresh token missing")

    payload = decode_refresh_token(token)
    user_id = payload.get("sub")

    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()

    if not user or not user.refresh_token_hash:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    # Validate that the presented token matches what we stored
    if not verify_token_hash(token, user.refresh_token_hash):
        raise HTTPException(status_code=401, detail="Refresh token mismatch — please log in again")

    # Issue new access token
    token_data = {
        "sub": str(user.id),
        "org_id": user.org_id,
        "role": user.role,
        "email": user.email,
    }
    new_access_token = create_access_token(token_data)

    # Rotate refresh token
    new_refresh = create_refresh_token(user.id)
    user.refresh_token_hash = hash_token(new_refresh)
    await db.commit()

    response.set_cookie(
        key=REFRESH_TOKEN_COOKIE,
        value=new_refresh,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=60 * 60 * 24 * 7
    )

    return AccessTokenResponse(access_token=new_access_token)


# ── Logout ────────────────────────────────────────────────────────────────

@router.post("/logout", response_model=MessageResponse)
async def logout(
    response: Response,
    current_user: UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Invalidate refresh token and clear cookie."""

    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one_or_none()
    if user:
        user.refresh_token_hash = None
        await db.commit()

    response.delete_cookie(REFRESH_TOKEN_COOKIE)
    return {"message": "Logged out successfully"}


# ── Me ────────────────────────────────────────────────────────────────────

@router.get("/me", response_model=UserRead)
async def get_me(current_user: UserRead = Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    return current_user


# ── Change password ───────────────────────────────────────────────────────

@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    payload: dict,
    current_user: UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one_or_none()

    if not verify_password(payload.get("current_password", ""), user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    user.password_hash = hash_password(payload.get("new_password", ""))
    await db.commit()
    return {"message": "Password changed successfully"}
