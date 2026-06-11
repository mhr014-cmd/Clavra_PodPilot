from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from app.database import Base

class QualityReport(Base):
    """Quality control inspection report — scoped to org."""
    __tablename__ = "quality_reports"
    id              = Column(Integer, primary_key=True, index=True)
    order_id        = Column(Integer, ForeignKey("production_orders.id", ondelete="SET NULL"), nullable=True)
    line_id         = Column(Integer, ForeignKey("production_lines.id",  ondelete="SET NULL"), nullable=True)
    org_id          = Column(Integer, ForeignKey("organizations.id",     ondelete="CASCADE"),  nullable=True, index=True)
    inspector_id    = Column(Integer, ForeignKey("users.id"),            nullable=True)
    defect_type     = Column(String(200), nullable=True)
    defect_count    = Column(Integer, default=0)
    total_checked   = Column(Integer, default=0)
    defect_rate     = Column(Float,   default=0.0)
    severity        = Column(String(50), default="minor")  # critical | major | minor
    notes           = Column(Text,    nullable=True)
    inspection_date = Column(DateTime(timezone=True), server_default=func.now())
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
