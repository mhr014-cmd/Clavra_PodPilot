from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from app.database import Base

class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    id          = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("knowledge_documents.id", ondelete="CASCADE"))
    org_id      = Column(Integer, nullable=True, index=True)
    chunk_index = Column(Integer)
    page_number = Column(Integer)
    content     = Column(Text, nullable=False)
    token_count = Column(Integer, default=0)
    # embedding vector(1536) is added via raw SQL migration — not via ORM
