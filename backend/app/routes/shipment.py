"""Shipments route — real PostgreSQL, org-scoped, auth-protected."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from datetime import datetime as _dt
from app.dependencies import get_db, get_current_user
from app.models.shipment import Shipment
from app.models.production import ProductionOrder
from app.schemas.auth import UserRead
from app.schemas.shipment import ShipmentCreate, ShipmentResponse

router = APIRouter()


async def _load_order_map(db: AsyncSession, order_ids: list[int]) -> dict:
    """Return {order_id: {order_no, order_style}} for given order ids."""
    if not order_ids:
        return {}
    result = await db.execute(
        select(ProductionOrder.id, ProductionOrder.order_no, ProductionOrder.style)
        .where(ProductionOrder.id.in_(order_ids))
    )
    return {
        row.id: {"order_no": row.order_no, "order_style": row.style}
        for row in result.all()
    }


def _enrich_shipments(shipments: list, order_map: dict) -> list[dict]:
    rows = []
    for s in shipments:
        order = order_map.get(s.order_id, {}) if s.order_id else {}
        rows.append({
            "id":               s.id,
            "shipment_no":      s.shipment_no,
            "buyer":            s.buyer,
            "destination":      s.destination,
            "carrier":          s.carrier,
            "status":           s.status,
            "eta":              s.eta.isoformat() if s.eta else None,
            "actual_departure": s.actual_departure.isoformat() if s.actual_departure else None,
            "order_id":         s.order_id,
            "org_id":           s.org_id,
            "created_at":       s.created_at.isoformat() if s.created_at else None,
            "order_no":         order.get("order_no"),
            "order_style":      order.get("order_style"),
        })
    return rows


@router.get("/")
async def get_shipments(
    status: Optional[str] = Query(None),
    buyer:  Optional[str] = Query(None),
    limit:  int           = Query(50, le=200),
    offset: int           = Query(0),
    current_user: UserRead    = Depends(get_current_user),
    db:           AsyncSession = Depends(get_db),
):
    q = select(Shipment).where(Shipment.org_id == current_user.org_id)
    if status:
        q = q.where(Shipment.status == status)
    if buyer:
        q = q.where(Shipment.buyer.ilike(f"%{buyer}%"))
    q = q.order_by(Shipment.id.desc()).limit(limit).offset(offset)
    result = await db.execute(q)
    shipments = result.scalars().all()

    order_ids = [s.order_id for s in shipments if s.order_id]
    order_map = await _load_order_map(db, order_ids)
    return _enrich_shipments(shipments, order_map)


@router.get("/unlinked-orders")
async def get_unlinked_orders(
    current_user: UserRead    = Depends(get_current_user),
    db:           AsyncSession = Depends(get_db),
):
    """Return orders that have no shipment linked — used by New Shipment form."""
    linked_result = await db.execute(
        select(Shipment.order_id).where(
            Shipment.org_id == current_user.org_id,
            Shipment.order_id.isnot(None),
        )
    )
    linked_ids = {row[0] for row in linked_result.all()}

    result = await db.execute(
        select(ProductionOrder.id, ProductionOrder.order_no,
               ProductionOrder.buyer, ProductionOrder.style,
               ProductionOrder.delivery_date)
        .where(ProductionOrder.org_id == current_user.org_id)
        .where(ProductionOrder.status != "Cancelled")
        .order_by(ProductionOrder.id.desc())
    )
    rows = result.all()
    return [
        {
            "id": r.id, "order_no": r.order_no, "buyer": r.buyer,
            "style": r.style,
            "delivery_date": r.delivery_date.isoformat() if r.delivery_date else None,
            "already_linked": r.id in linked_ids,
        }
        for r in rows
    ]


@router.get("/{shipment_id}")
async def get_shipment(
    shipment_id: int,
    current_user: UserRead    = Depends(get_current_user),
    db:           AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Shipment).where(
            Shipment.id == shipment_id,
            Shipment.org_id == current_user.org_id
        )
    )
    s = result.scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail="Shipment not found")
    order_map = await _load_order_map(db, [s.order_id] if s.order_id else [])
    return _enrich_shipments([s], order_map)[0]


@router.post("/", status_code=201)
async def create_shipment(
    payload: ShipmentCreate,
    current_user: UserRead    = Depends(get_current_user),
    db:           AsyncSession = Depends(get_db),
):
    existing = await db.execute(
        select(Shipment).where(Shipment.shipment_no == payload.shipment_no)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Shipment number already exists")

    # If an order_id is given, verify it belongs to this org
    if payload.order_id:
        ord_check = await db.execute(
            select(ProductionOrder.id).where(
                ProductionOrder.id == payload.order_id,
                ProductionOrder.org_id == current_user.org_id,
            )
        )
        if not ord_check.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Order not found in your organisation")

    s = Shipment(
        shipment_no=payload.shipment_no,
        order_id=payload.order_id,
        buyer=payload.buyer,
        destination=payload.destination,
        carrier=payload.carrier,
        eta=payload.eta,
        actual_departure=payload.actual_departure,
        status="Pending",
        org_id=current_user.org_id,
        created_by=current_user.id,
    )
    db.add(s)
    await db.commit()
    await db.refresh(s)

    order_map = await _load_order_map(db, [s.order_id] if s.order_id else [])
    return _enrich_shipments([s], order_map)[0]


@router.put("/{shipment_id}")
async def update_shipment(
    shipment_id: int,
    payload: dict,
    current_user: UserRead    = Depends(get_current_user),
    db:           AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Shipment).where(
            Shipment.id == shipment_id,
            Shipment.org_id == current_user.org_id
        )
    )
    s = result.scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail="Shipment not found")
    allowed = {"status", "eta", "actual_departure", "actual_arrival", "carrier", "order_id", "destination"}
    _date_fields = {"eta", "actual_departure", "actual_arrival"}
    for k, v in payload.items():
        if k in allowed:
            if k in _date_fields and isinstance(v, str) and v:
                try:
                    v = _dt.fromisoformat(v.replace("Z", "+00:00"))
                except ValueError:
                    pass
            setattr(s, k, v)
    await db.commit()
    await db.refresh(s)
    order_map = await _load_order_map(db, [s.order_id] if s.order_id else [])
    return _enrich_shipments([s], order_map)[0]
