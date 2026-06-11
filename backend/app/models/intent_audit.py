from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.sql import func
from app.database import Base

class IntentAudit(Base):
    """Audit log for every AI query — used to measure intent accuracy."""
    __tablename__ = "intent_audit"
    id              = Column(Integer, primary_key=True, index=True)
    org_id          = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    user_id         = Column(Integer, ForeignKey("users.id"),         nullable=True)
    message         = Column(Text,      nullable=False)
    detected_intent = Column(String(100), nullable=True)
    confidence      = Column(Float,     nullable=True)
    action_type     = Column(String(50), nullable=True)
    was_correct     = Column(Boolean,   nullable=True)  # set by user feedback
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
