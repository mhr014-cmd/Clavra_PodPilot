from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    """
    Platform user — belongs to one Organisation.
    password_hash stores bcrypt hash — never plain text.
    refresh_token_hash stores bcrypt hash of latest refresh token
    so logout can invalidate it without Redis dependency.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    # ── Identity ──────────────────────────────────────────────────────────
    full_name = Column(String(200), nullable=False)

    email = Column(String(255), unique=True, index=True, nullable=False)

    password_hash = Column(String(255), nullable=False)

    # ── Org + role ────────────────────────────────────────────────────────
    org_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )

    role = Column(String(50), default="viewer", nullable=False)
    # Values: admin | manager | supervisor | qc_inspector | viewer

    # ── Auth ──────────────────────────────────────────────────────────────
    refresh_token_hash = Column(String(255), nullable=True)
    # Stores bcrypt hash of current refresh token — cleared on logout

    is_active = Column(Boolean, default=True)

    is_verified = Column(Boolean, default=False)

    # ── Timestamps ────────────────────────────────────────────────────────
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    last_login_at = Column(DateTime(timezone=True), nullable=True)
