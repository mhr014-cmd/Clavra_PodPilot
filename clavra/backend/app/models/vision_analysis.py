from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, JSON
from sqlalchemy.sql import func
from app.database import Base

class VisionAnalysis(Base):
    """Persisted result of a GPT-4o Vision analysis."""
    __tablename__ = "vision_analyses"
    id                 = Column(Integer, primary_key=True, index=True)
    org_id             = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    user_id            = Column(Integer, ForeignKey("users.id"),         nullable=True)
    image_filename     = Column(String(255), nullable=True)
    analysis_type      = Column(String(50),  nullable=True)
    findings           = Column(JSON,        nullable=True)
    defect_rate        = Column(Float,       nullable=True)
    confidence         = Column(Float,       nullable=True)
    recommended_action = Column(Text,        nullable=True)
    summary            = Column(Text,        nullable=True)
    created_at         = Column(DateTime(timezone=True), server_default=func.now())
