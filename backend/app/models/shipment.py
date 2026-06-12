from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class Shipment(Base):
    """Shipment record — scoped to org_id."""
    __tablename__ = "shipments"

    id = Column(Integer, primary_key=True, index=True)

    shipment_no  = Column(String(100), unique=True, index=True, nullable=False)
    buyer        = Column(String(200), nullable=True)
    destination  = Column(String(200), nullable=True)
    carrier      = Column(String(200), nullable=True)
    port_of_loading = Column(String(200), nullable=True)

    status = Column(String(50), default="Pending")
    # Pending | In Transit | Customs | Delivered | Delayed | Cancelled

    order_id = Column(
        Integer,
        ForeignKey("production_orders.id", ondelete="SET NULL"),
        nullable=True
    )

    # ── Dates ─────────────────────────────────────────────────────────────
    eta              = Column(DateTime(timezone=True), nullable=True)
    actual_departure = Column(DateTime(timezone=True), nullable=True)
    actual_arrival   = Column(DateTime(timezone=True), nullable=True)

    # ── Multi-tenant ──────────────────────────────────────────────────────
    org_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )

    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
