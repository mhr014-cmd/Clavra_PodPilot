"""
Factory Summary Service — pulls a live snapshot across orders, shipments, and inventory.
Used by the AI greeting and general_status intents.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.production import ProductionOrder
from app.models.shipment import Shipment
from app.models.inventory import Inventory


async def get_factory_snapshot(db: AsyncSession, org_id: int) -> dict:
    """Return counts and highlights across the entire factory."""

    # ── Orders ────────────────────────────────────────────────────────────
    order_result = await db.execute(
        select(ProductionOrder.status, func.count(ProductionOrder.id))
        .where(ProductionOrder.org_id == org_id)
        .group_by(ProductionOrder.status)
    )
    order_rows = order_result.all()
    order_counts = {row[0]: row[1] for row in order_rows}
    total_orders = sum(order_counts.values())
    active_orders = sum(v for k, v in order_counts.items()
                        if k not in ("Completed", "Cancelled"))

    # ── Shipments ─────────────────────────────────────────────────────────
    ship_result = await db.execute(
        select(Shipment.status, func.count(Shipment.id))
        .where(Shipment.org_id == org_id)
        .group_by(Shipment.status)
    )
    ship_rows = ship_result.all()
    ship_counts = {row[0]: row[1] for row in ship_rows}
    total_ships  = sum(ship_counts.values())
    in_transit   = ship_counts.get("In Transit", 0)
    pending_ships = ship_counts.get("Pending", 0)
    delayed_ships = ship_counts.get("Delayed", 0)

    # ── Inventory alerts ──────────────────────────────────────────────────
    low_result = await db.execute(
        select(func.count(Inventory.id))
        .where(Inventory.status.in_(["Low Stock", "Critical", "Out of Stock"]))
    )
    low_stock_count = low_result.scalar() or 0

    return {
        "total_orders":   total_orders,
        "active_orders":  active_orders,
        "order_counts":   order_counts,
        "total_ships":    total_ships,
        "ship_counts":    ship_counts,
        "in_transit":     in_transit,
        "pending_ships":  pending_ships,
        "delayed_ships":  delayed_ships,
        "low_stock_count": low_stock_count,
    }


def format_snapshot_message(snap: dict, greeting: str = "") -> str:
    """Format snapshot into a natural language message."""
    parts = []

    if greeting:
        parts.append(greeting)

    # Orders section
    order_counts = snap["order_counts"]
    if snap["total_orders"] == 0:
        parts.append("**📋 Orders:** No production orders yet.")
    else:
        active = snap["active_orders"]
        completed = order_counts.get("Completed", 0)
        cancelled = order_counts.get("Cancelled", 0)
        status_breakdown = ", ".join(
            f"{count} {status.lower()}"
            for status, count in order_counts.items()
            if count > 0
        )
        parts.append(
            f"**📋 Orders:** {snap['total_orders']} total "
            f"({active} active, {completed} completed"
            + (f", {cancelled} cancelled" if cancelled else "")
            + f") — {status_breakdown}"
        )

    # Shipments section — show all statuses, not just in-transit/pending
    ship_counts = snap.get("ship_counts", {})
    total_ships  = snap.get("total_ships", 0)
    if total_ships == 0:
        parts.append("**🚢 Shipments:** No shipments on record.")
    else:
        status_icon = {
            "In Transit": "🚢", "Pending": "🟡", "Delayed": "🔴",
            "Delivered": "✅", "Cancelled": "❌", "Customs": "🔵",
        }
        breakdown = ", ".join(
            f"{status_icon.get(st, '⚪')} {cnt} {st.lower()}"
            for st, cnt in ship_counts.items() if cnt > 0
        )
        delayed = snap.get("delayed_ships", 0)
        alert = " ⚠️ *Check delayed shipments!*" if delayed > 0 else ""
        parts.append(f"**🚢 Shipments:** {total_ships} total — {breakdown}{alert}")

    # Inventory alerts
    if snap["low_stock_count"] > 0:
        parts.append(
            f"**⚠️ Stock Alert:** {snap['low_stock_count']} material(s) are low or critical — "
            f"type *'check my stock'* for details."
        )
    else:
        parts.append("**📦 Inventory:** All stock levels look healthy.")

    parts.append(
        "\n💡 *Ask me anything — 'Show my orders', 'Any shipments delayed?', "
        "'Check fabric stock', or 'How efficient is Line A?'*"
    )

    return "\n\n".join(parts)
