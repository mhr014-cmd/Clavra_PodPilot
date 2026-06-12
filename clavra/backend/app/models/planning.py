from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.sql import func
from app.database import Base

class PlanningTNA(Base):
    """Time & Action calendar entry."""
    __tablename__ = "planning_tna"
    id           = Column(Integer, primary_key=True, index=True)
    order_id     = Column(Integer, ForeignKey("production_orders.id", ondelete="CASCADE"), nullable=True)
    org_id       = Column(Integer, ForeignKey("organizations.id",     ondelete="CASCADE"), nullable=True, index=True)
    task_name    = Column(String(300), nullable=False)
    responsible  = Column(String(200), nullable=True)
    planned_date = Column(DateTime(timezone=True), nullable=True)
    actual_date  = Column(DateTime(timezone=True), nullable=True)
    is_completed = Column(Boolean, default=False)
    notes        = Column(Text,    nullable=True)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())
