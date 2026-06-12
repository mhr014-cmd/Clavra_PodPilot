from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from app.database import Base

class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"
    id            = Column(Integer, primary_key=True, index=True)
    org_id        = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    filename      = Column(String(255), nullable=False)
    original_name = Column(String(255), nullable=False)
    doc_type      = Column(String(50), nullable=True)  # sop|manual|policy|quality_standard
    page_count    = Column(Integer, default=0)
    chunk_count   = Column(Integer, default=0)
    uploaded_by   = Column(Integer, ForeignKey("users.id"), nullable=True)
    uploaded_at   = Column(DateTime(timezone=True), server_default=func.now())
