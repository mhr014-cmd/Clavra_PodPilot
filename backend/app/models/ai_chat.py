from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Float, JSON
from sqlalchemy.sql import func
from app.database import Base


class AIConversation(Base):
    """Chat conversation thread — one user, one org."""
    __tablename__ = "ai_conversations"

    id    = Column(Integer, primary_key=True, index=True)
    title = Column(String(300), nullable=False, default="New Conversation")

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    org_id  = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"),
                     nullable=True, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AIMessage(Base):
    """
    Individual message in a conversation.
    Stores the detected intent, confidence, and which pipeline branch handled it.
    """
    __tablename__ = "ai_messages"

    id              = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("ai_conversations.id", ondelete="CASCADE"))

    role    = Column(String(20), nullable=False)   # user | assistant
    message = Column(Text, nullable=False)

    # ── AI metadata ───────────────────────────────────────────────────────
    intent      = Column(String(100), nullable=True)   # e.g. cancel_order
    confidence  = Column(Float, nullable=True)          # 0.0 – 1.0
    action_type = Column(String(50), nullable=True)     # business_action | analytics_question | …
    sql_used    = Column(Text, nullable=True)            # AI-generated SQL if branch B
    sources     = Column(JSON, nullable=True)            # RAG source citations if branch C

    # ── Multi-tenant ──────────────────────────────────────────────────────
    org_id  = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
