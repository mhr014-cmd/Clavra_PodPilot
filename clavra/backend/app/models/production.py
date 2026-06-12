from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float
from sqlalchemy.sql import func
from app.database import Base


class ProductionOrder(Base):
    """Production order — scoped to org_id for multi-tenant isolation."""
    __tablename__ = "production_orders"

    id = Column(Integer, primary_key=True, index=True)

    # ── Order identity ────────────────────────────────────────────────────
    order_no = Column(String(100), unique=True, nullable=False, index=True)
    buyer    = Column(String(200), nullable=False)
    style    = Column(String(200), nullable=False)

    # ── Quantities ────────────────────────────────────────────────────────
    quantity     = Column(Integer, nullable=False, default=0)
    produced_qty = Column(Integer, default=0)
    defect_qty   = Column(Integer, default=0)

    # ── Status + line ─────────────────────────────────────────────────────
    status = Column(String(50), default="Pending")
    # Pending | Cutting | Sewing | Finishing | Packing | Completed | Cancelled

    line_id = Column(
        Integer,
        ForeignKey("production_lines.id", ondelete="SET NULL"),
        nullable=True
    )

    # ── Dates ─────────────────────────────────────────────────────────────
    start_date    = Column(DateTime(timezone=True), nullable=True)
    end_date      = Column(DateTime(timezone=True), nullable=True)
    delivery_date = Column(DateTime(timezone=True), nullable=True)

    # ── Multi-tenant ──────────────────────────────────────────────────────
    org_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )

    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    # ── Timestamps ────────────────────────────────────────────────────────
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
