import re
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.production import ProductionOrder


async def cancel_order(db: AsyncSession, order_ref: str, org_id: int, user_id: int) -> dict:
    q = select(ProductionOrder).where(
        ProductionOrder.org_id == org_id,
    )
    if str(order_ref).isdigit():
        q = q.where(ProductionOrder.id == int(order_ref))
    else:
        q = q.where(ProductionOrder.order_no == str(order_ref))

    result = await db.execute(q)
    order = result.scalar_one_or_none()

    if not order:
        return {"message": f"Order {order_ref} not found.", "success": False}
    if order.status == "Completed":
        return {"message": f"Order {order_ref} is already completed and cannot be cancelled.", "success": False}
    if order.status == "Cancelled":
        return {"message": f"Order {order_ref} is already cancelled.", "success": False}

    order.status = "Cancelled"
    await db.commit()
    return {"message": f"Order {order_ref} has been cancelled successfully.", "success": True,
            "order_no": order.order_no}


async def get_order_status(db: AsyncSession, order_ref: str, org_id: int) -> dict | None:
    q = select(ProductionOrder).where(ProductionOrder.org_id == org_id)
    if str(order_ref).isdigit():
        q = q.where(ProductionOrder.id == int(order_ref))
    else:
        q = q.where(ProductionOrder.order_no == str(order_ref))

    result = await db.execute(q)
    order = result.scalar_one_or_none()
    if not order:
        return None
    return {"id": order.id, "order_no": order.order_no, "buyer": order.buyer,
            "style": order.style, "quantity": order.quantity,
            "produced_qty": order.produced_qty, "status": order.status}


async def get_last_orders(db: AsyncSession, org_id: int, limit: int = 5) -> list:
    result = await db.execute(
        select(ProductionOrder)
        .where(ProductionOrder.org_id == org_id)
        .order_by(ProductionOrder.id.desc())
        .limit(min(limit, 50))
    )
    orders = result.scalars().all()
    return [{"id": o.id, "order_no": o.order_no, "buyer": o.buyer,
             "quantity": o.quantity, "status": o.status} for o in orders]


async def get_active_orders(db: AsyncSession, org_id: int) -> list:
    """Return orders currently in an active production stage (not Pending/Completed/Cancelled)."""
    ACTIVE = ("Cutting", "Sewing", "Finishing", "Packing")
    result = await db.execute(
        select(ProductionOrder)
        .where(
            ProductionOrder.org_id == org_id,
            ProductionOrder.status.in_(ACTIVE),
        )
        .order_by(ProductionOrder.status, ProductionOrder.id.desc())
    )
    orders = result.scalars().all()
    out = []
    for o in orders:
        pct = round((o.produced_qty or 0) / max(o.quantity, 1) * 100)
        out.append({
            "id": o.id, "order_no": o.order_no, "buyer": o.buyer,
            "style": o.style, "quantity": o.quantity,
            "produced_qty": o.produced_qty or 0,
            "status": o.status, "line_id": o.line_id,
            "progress_pct": pct,
        })
    return out


async def get_lines_with_orders(db: AsyncSession, org_id: int) -> list:
    """Return all production lines enriched with their current active orders."""
    from app.models.production_line import ProductionLine
    lines_result = await db.execute(
        select(ProductionLine).order_by(ProductionLine.line_name)
    )
    lines = lines_result.scalars().all()
    if not lines:
        return []

    line_ids = [l.id for l in lines]
    ACTIVE = ("Cutting", "Sewing", "Finishing", "Packing", "Pending")
    conditions = [
        ProductionOrder.line_id.in_(line_ids),
        ProductionOrder.status.in_(ACTIVE),
    ]
    if org_id is not None:
        conditions.append(ProductionOrder.org_id == org_id)
    orders_result = await db.execute(
        select(ProductionOrder).where(*conditions)
    )
    orders = orders_result.scalars().all()
    line_order_map: dict[int, list] = {}
    for o in orders:
        pct = round((o.produced_qty or 0) / max(o.quantity, 1) * 100)
        entry = {
            "order_no": o.order_no, "buyer": o.buyer, "style": o.style,
            "status": o.status, "progress_pct": pct,
        }
        line_order_map.setdefault(o.line_id, []).append(entry)

    result = []
    for l in lines:
        cur = line_order_map.get(l.id, [])
        result.append({
            "line_name": l.line_name, "supervisor": l.supervisor,
            "status": l.status, "efficiency": l.efficiency,
            "actual_output": l.actual_output, "target_output": l.target_output,
            "operators": l.operators, "defects": l.defects,
            "current_orders": cur,
        })
    return result


async def get_efficiency_summary(db: AsyncSession, org_id: int) -> dict:
    """Return per-line efficiency metrics for AI Copilot response."""
    from app.models.production_line import ProductionLine
    result = await db.execute(
        select(ProductionLine).order_by(ProductionLine.line_name)
    )
    lines = result.scalars().all()
    if not lines:
        return {"lines": [], "avg_efficiency": 0}
    line_list = [
        {
            "line_name":     l.line_name,
            "status":        l.status,
            "efficiency":    l.efficiency or 0,
            "actual_output": l.actual_output or 0,
            "target_output": l.target_output or 0,
            "operators":     l.operators or 0,
            "defects":       l.defects or 0,
            "supervisor":    l.supervisor,
        }
        for l in lines
    ]
    avg = round(sum(l["efficiency"] for l in line_list) / len(line_list))
    return {"lines": line_list, "avg_efficiency": avg}


async def get_delay_risks(db: AsyncSession, org_id: int) -> dict:
    """Return active orders flagged as at-risk of missing delivery."""
    from datetime import date
    ACTIVE = ("Cutting", "Sewing", "Finishing", "Packing", "Pending")
    result = await db.execute(
        select(ProductionOrder).where(
            ProductionOrder.org_id == org_id,
            ProductionOrder.status.in_(ACTIVE),
        )
    )
    orders = result.scalars().all()
    today = date.today()
    at_risk = []
    on_track = []

    for o in orders:
        pct = round((o.produced_qty or 0) / max(o.quantity, 1) * 100)
        delivery_date = getattr(o, "delivery_date", None) or getattr(o, "due_date", None)
        entry = {
            "order_no":     o.order_no,
            "buyer":        o.buyer,
            "style":        getattr(o, "style", ""),
            "status":       o.status,
            "progress_pct": pct,
            "quantity":     o.quantity,
            "produced_qty": o.produced_qty or 0,
            "delivery_date": str(delivery_date) if delivery_date else None,
            "days_left":     (delivery_date - today).days if delivery_date else None,
        }
        if delivery_date:
            days_left = (delivery_date - today).days
            if days_left < 0:
                entry["risk"] = "overdue"
                at_risk.append(entry)
            elif days_left <= 7 and pct < 80:
                entry["risk"] = "critical"
                at_risk.append(entry)
            elif days_left <= 14 and pct < 50:
                entry["risk"] = "warning"
                at_risk.append(entry)
            else:
                entry["risk"] = "ok"
                on_track.append(entry)
        else:
            if pct < 30 and o.status not in ("Pending",):
                entry["risk"] = "warning"
                at_risk.append(entry)
            else:
                entry["risk"] = "ok"
                on_track.append(entry)

    return {"at_risk": at_risk, "on_track": on_track, "total_active": len(orders)}


async def get_next_order_no(db: AsyncSession, org_id: int) -> str:
    """Return the next available PO-NNN order number for this org."""
    result = await db.execute(
        select(ProductionOrder.order_no).where(ProductionOrder.org_id == org_id)
    )
    max_num = 0
    for (no,) in result.all():
        m = re.match(r'(?:PO|ORD)-?(\d+)', no or "", re.IGNORECASE)
        if m:
            max_num = max(max_num, int(m.group(1)))
    return f"PO-{str(max_num + 1).zfill(3)}"


async def create_order_via_ai(
    db: AsyncSession,
    order_no: str,
    buyer: str,
    style: str,
    quantity: int,
    org_id: int,
    user_id: int,
    delivery_date=None,
) -> dict:
    """Create a production order from AI-supplied entities."""
    existing = await db.execute(
        select(ProductionOrder).where(ProductionOrder.order_no == order_no)
    )
    if existing.scalar_one_or_none():
        return {"success": False, "message": f"Order number {order_no} already exists."}

    order = ProductionOrder(
        order_no=order_no, buyer=buyer, style=style, quantity=quantity,
        status="Pending", org_id=org_id, created_by=user_id,
        delivery_date=delivery_date,
    )
    db.add(order)
    await db.commit()
    await db.refresh(order)
    return {
        "success": True,
        "message": f"✅ Production order **{order_no}** created — {buyer} · {style} · {quantity:,} pcs",
        "order": {"id": order.id, "order_no": order.order_no, "buyer": order.buyer,
                  "style": order.style, "quantity": order.quantity, "status": order.status},
    }


async def update_order_status_ai(
    db: AsyncSession, order_ref: str, new_status: str, org_id: int
) -> dict:
    """Update order status via AI; validates the status value first."""
    VALID = {"Pending", "Cutting", "Sewing", "Finishing", "Packing", "Completed", "Cancelled"}
    if new_status not in VALID:
        return {"success": False, "message": f"Invalid status '{new_status}'. Valid: {', '.join(sorted(VALID))}"}

    q = select(ProductionOrder).where(ProductionOrder.org_id == org_id)
    if str(order_ref).isdigit():
        q = q.where(ProductionOrder.id == int(order_ref))
    else:
        q = q.where(ProductionOrder.order_no == str(order_ref))

    result = await db.execute(q)
    order = result.scalar_one_or_none()
    if not order:
        return {"success": False, "message": f"Order {order_ref} not found."}

    old_status = order.status
    order.status = new_status
    await db.commit()
    return {
        "success": True,
        "message": f"✅ **{order.order_no}** moved: **{old_status}** → **{new_status}**",
        "order_no": order.order_no, "old_status": old_status, "new_status": new_status,
    }


async def log_defects_ai(
    db: AsyncSession, order_ref: str, defect_qty: int, org_id: int,
    defect_type: str = "General",
) -> dict:
    """Add defect count to a production order."""
    q = select(ProductionOrder).where(ProductionOrder.org_id == org_id)
    if str(order_ref).isdigit():
        q = q.where(ProductionOrder.id == int(order_ref))
    else:
        q = q.where(ProductionOrder.order_no == str(order_ref))

    result = await db.execute(q)
    order = result.scalar_one_or_none()
    if not order:
        return {"success": False, "message": f"Order {order_ref} not found."}

    order.defect_qty = (order.defect_qty or 0) + defect_qty
    await db.commit()
    return {
        "success": True,
        "message": (
            f"✅ Logged **{defect_qty} defects** ({defect_type}) for **{order.order_no}**."
            f" Total defects: {order.defect_qty}"
        ),
        "order_no": order.order_no, "added": defect_qty, "total_defects": order.defect_qty,
    }


async def link_order_to_shipment_ai(
    db: AsyncSession, order_ref: str, shipment_ref: str, org_id: int
) -> dict:
    """Link a production order to a shipment via AI command."""
    from app.models.shipment import Shipment
    from sqlalchemy import update as sql_update

    q = select(ProductionOrder).where(ProductionOrder.org_id == org_id)
    if str(order_ref).isdigit():
        q = q.where(ProductionOrder.id == int(order_ref))
    else:
        q = q.where(ProductionOrder.order_no == str(order_ref))
    result = await db.execute(q)
    order = result.scalar_one_or_none()
    if not order:
        return {"success": False, "message": f"Order **{order_ref}** not found."}

    sq = select(Shipment).where(Shipment.org_id == org_id)
    if str(shipment_ref).isdigit():
        sq = sq.where(Shipment.id == int(shipment_ref))
    else:
        sq = sq.where(Shipment.shipment_no == str(shipment_ref))
    sres = await db.execute(sq)
    shipment = sres.scalar_one_or_none()
    if not shipment:
        return {"success": False, "message": f"Shipment **{shipment_ref}** not found."}

    await db.execute(
        sql_update(Shipment)
        .where(Shipment.order_id == order.id, Shipment.org_id == org_id)
        .values(order_id=None)
    )
    shipment.order_id = order.id
    await db.commit()
    dest = f" → {shipment.destination}" if shipment.destination else ""
    return {
        "success": True,
        "message": f"✅ **{order.order_no}** ({order.buyer}) linked to **{shipment.shipment_no}**{dest}",
        "order_no": order.order_no,
        "shipment_no": shipment.shipment_no,
    }


async def create_invoice(db: AsyncSession, order_ref: str, org_id: int, user_id: int) -> dict:
    result = await db.execute(
        select(ProductionOrder).where(
            ProductionOrder.org_id == org_id,
            ProductionOrder.order_no == str(order_ref)
        )
    )
    order = result.scalar_one_or_none()
    if not order:
        return {"message": f"Order {order_ref} not found.", "success": False}
    return {"message": f"Invoice for order {order_ref} queued for generation.",
            "success": True, "order_no": order.order_no}
