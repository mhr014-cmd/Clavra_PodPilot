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
