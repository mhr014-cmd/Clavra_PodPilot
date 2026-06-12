from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.database import Base


class Organization(Base):
    """
    Multi-tenant organisation record.
    Every user, order, shipment, and AI query belongs to one org.
    """
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(200), nullable=False)

    slug = Column(String(100), unique=True, index=True, nullable=False)

    plan = Column(String(50), default="starter")
    # Plans: starter | professional | enterprise

    is_active = Column(Boolean, default=True)

    max_users = Column(Integer, default=10)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )
