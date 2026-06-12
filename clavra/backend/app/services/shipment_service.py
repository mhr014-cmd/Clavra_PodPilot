import re
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.shipment import Shipment


async def get_recent_shipments(db: AsyncSession, org_id: int, limit: int = 5) -> list:
    result = await db.execute(
        select(Shipment)
        .where(Shipment.org_id == org_id)
        .order_by(Shipment.id.desc())
        .limit(min(limit, 50))
    )
    shipments = result.scalars().all()
    return [{"id": s.id, "shipment_no": s.shipment_no, "buyer": s.buyer,
             "destination": s.destination, "status": s.status,
             "eta": str(s.eta) if s.eta else None} for s in shipments]


async def cancel_shipment(db: AsyncSession, shipment_ref: str, org_id: int) -> dict:
    q = select(Shipment).where(Shipment.org_id == org_id)
    if str(shipment_ref).isdigit():
        q = q.where(Shipment.id == int(shipment_ref))
    else:
        q = q.where(Shipment.shipment_no == str(shipment_ref))

    result = await db.execute(q)
    s = result.scalar_one_or_none()
    if not s:
        return {"message": f"Shipment '{shipment_ref}' not found.", "success": False}
    if s.status in ("Delivered", "Cancelled"):
        return {"message": f"Shipment {s.shipment_no} is already {s.status} and cannot be cancelled.", "success": False}

    s.status = "Cancelled"
    await db.commit()
    return {"message": f"Shipment **{s.shipment_no}** to {s.destination} has been cancelled.", "success": True}


async def get_shipment_by_order(db: AsyncSession, order_id: int, org_id: int) -> dict | None:
    result = await db.execute(
        select(Shipment)
        .where(Shipment.org_id == org_id)
        .where(Shipment.order_id == order_id)
        .order_by(Shipment.id.desc())
        .limit(1)
    )
    s = result.scalar_one_or_none()
    if not s:
        return None
    return {"id": s.id, "shipment_no": s.shipment_no, "buyer": s.buyer,
            "destination": s.destination, "status": s.status,
            "eta": str(s.eta) if s.eta else None}


async def get_next_shipment_no(db: AsyncSession, org_id: int) -> str:
    """Return the next available SHP-NNN shipment number for this org."""
    result = await db.execute(
        select(Shipment.shipment_no).where(Shipment.org_id == org_id)
    )
    max_num = 0
    for (no,) in result.all():
        m = re.match(r'SHP-?(\d+)', no or "", re.IGNORECASE)
        if m:
            max_num = max(max_num, int(m.group(1)))
    return f"SHP-{str(max_num + 1).zfill(3)}"


async def create_shipment_via_ai(
    db: AsyncSession,
    shipment_no: str,
    org_id: int,
    destination: str | None = None,
    carrier: str | None = None,
    buyer: str | None = None,
    order_no: str | None = None,
    eta=None,
) -> dict:
    """Create a shipment from AI-supplied entities."""
    from app.models.production import ProductionOrder

    existing = await db.execute(
        select(Shipment).where(Shipment.shipment_no == shipment_no)
    )
    if existing.scalar_one_or_none():
        return {"success": False, "message": f"Shipment {shipment_no} already exists."}

    # Resolve linked order
    order_id = None
    if order_no:
        ord_res = await db.execute(
            select(ProductionOrder).where(
                ProductionOrder.order_no == order_no,
                ProductionOrder.org_id == org_id,
            )
        )
        ord_obj = ord_res.scalar_one_or_none()
        if ord_obj:
            order_id = ord_obj.id
            if not buyer:
                buyer = ord_obj.buyer

    shipment = Shipment(
        shipment_no=shipment_no, org_id=org_id, destination=destination,
        carrier=carrier, buyer=buyer, order_id=order_id, status="Pending", eta=eta,
    )
    db.add(shipment)
    await db.commit()
    await db.refresh(shipment)
    dest_str = f" → {destination}" if destination else ""
    link_str = f" (linked to {order_no})" if order_no and order_id else ""
    return {
        "success": True,
        "message": f"✅ Shipment **{shipment_no}** booked{dest_str}{link_str}",
        "shipment": {
            "id": shipment.id, "shipment_no": shipment.shipment_no,
            "destination": shipment.destination, "carrier": shipment.carrier,
            "status": shipment.status,
        },
    }


async def get_shipment_status(db: AsyncSession, shipment_ref: str, org_id: int) -> dict | None:
    q = select(Shipment).where(Shipment.org_id == org_id)
    if str(shipment_ref).isdigit():
        q = q.where(Shipment.id == int(shipment_ref))
    else:
        q = q.where(Shipment.shipment_no == str(shipment_ref))

    result = await db.execute(q)
    s = result.scalar_one_or_none()
    if not s:
        return None
    return {"id": s.id, "shipment_no": s.shipment_no, "buyer": s.buyer,
            "destination": s.destination, "status": s.status,
            "eta": str(s.eta) if s.eta else None}
