"""Production Orders route — real PostgreSQL, org-scoped, auth-protected."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from app.dependencies import get_db, get_current_user
from app.models.production import ProductionOrder
from app.models.shipment import Shipment
from app.schemas.auth import UserRead
from app.schemas.production import ProductionCreate, ProductionResponse

router = APIRouter()


def _enrich_orders(orders: list, shipment_map: dict) -> list[dict]:
    """Merge shipment data into order dicts and compute progress %."""
    rows = []
    for o in orders:
        ship = shipment_map.get(o.id, {})
        pct = round((o.produced_qty or 0) / max(o.quantity, 1) * 100)
        rows.append({
            "id":            o.id,
            "order_no":      o.order_no,
            "buyer":         o.buyer,
            "style":         o.style,
            "quantity":      o.quantity,
            "produced_qty":  o.produced_qty or 0,
            "defect_qty":    o.defect_qty   or 0,
            "status":        o.status,
            "line_id":       o.line_id,
            "delivery_date": o.delivery_date.isoformat() if o.delivery_date else None,
            "org_id":        o.org_id,
            "created_at":    o.created_at.isoformat() if o.created_at else None,
            "progress_pct":  pct,
            "shipment_no":   ship.get("shipment_no"),
            "shipment_id":   ship.get("shipment_id"),
            "shipment_status": ship.get("shipment_status"),
        })
    return rows


async def _load_shipment_map(db: AsyncSession, order_ids: list[int]) -> dict:
    """Return {order_id: {shipment_no, shipment_id, shipment_status}} for given order ids."""
    if not order_ids:
        return {}
    result = await db.execute(
        select(Shipment.order_id, Shipment.id, Shipment.shipment_no, Shipment.status)
        .where(Shipment.order_id.in_(order_ids))
    )
    # One shipment per order (take first if multiple)
    ship_map: dict = {}
    for row in result.all():
        if row.order_id not in ship_map:
            ship_map[row.order_id] = {
                "shipment_no":     row.shipment_no,
                "shipment_id":     row.id,
                "shipment_status": row.status,
            }
    return ship_map


@router.get("/")
async def get_orders(
    status: Optional[str] = Query(None),
    buyer:  Optional[str] = Query(None),
    limit:  int           = Query(50, le=200),
    offset: int           = Query(0),
    current_user: UserRead    = Depends(get_current_user),
    db:           AsyncSession = Depends(get_db),
):
    """List all orders for this organisation — enriched with linked shipment data."""
    q = select(ProductionOrder).where(
        ProductionOrder.org_id == current_user.org_id
    )
    if status:
        q = q.where(ProductionOrder.status == status)
    if buyer:
        q = q.where(ProductionOrder.buyer.ilike(f"%{buyer}%"))
    q = q.order_by(ProductionOrder.id.desc()).limit(limit).offset(offset)
    result = await db.execute(q)
    orders = result.scalars().all()

    ship_map = await _load_shipment_map(db, [o.id for o in orders])
    return _enrich_orders(orders, ship_map)


@router.get("/summary")
async def orders_summary(
    current_user: UserRead    = Depends(get_current_user),
    db:           AsyncSession = Depends(get_db),
):
    """KPI summary counts grouped by status."""
    result = await db.execute(
        select(ProductionOrder.status, func.count(ProductionOrder.id).label("count"))
        .where(ProductionOrder.org_id == current_user.org_id)
        .group_by(ProductionOrder.status)
    )
    rows = result.all()
    return {r.status: r.count for r in rows}


@router.get("/{order_id}")
async def get_order(
    order_id: int,
    current_user: UserRead    = Depends(get_current_user),
    db:           AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ProductionOrder).where(
            ProductionOrder.id     == order_id,
            ProductionOrder.org_id == current_user.org_id
        )
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    ship_map = await _load_shipment_map(db, [order.id])
    return _enrich_orders([order], ship_map)[0]


@router.post("/", status_code=201)
async def create_order(
    payload: ProductionCreate,
    current_user: UserRead    = Depends(get_current_user),
    db:           AsyncSession = Depends(get_db),
):
    existing = await db.execute(
        select(ProductionOrder).where(ProductionOrder.order_no == payload.order_no)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Order number already exists")
    order = ProductionOrder(
        order_no=payload.order_no, buyer=payload.buyer,
        style=payload.style, quantity=payload.quantity,
        delivery_date=payload.delivery_date,
        status="Pending", org_id=current_user.org_id,
        created_by=current_user.id,
    )
    db.add(order)
    await db.commit()
    await db.refresh(order)
    return _enrich_orders([order], {})[0]


@router.put("/{order_id}")
async def update_order(
    order_id: int,
    payload:  dict,
    current_user: UserRead    = Depends(get_current_user),
    db:           AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ProductionOrder).where(
            ProductionOrder.id == order_id,
            ProductionOrder.org_id == current_user.org_id
        )
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    allowed = {"status", "produced_qty", "defect_qty", "line_id", "delivery_date"}
    for k, v in payload.items():
        if k in allowed:
            setattr(order, k, v)
    await db.commit()
    await db.refresh(order)
    ship_map = await _load_shipment_map(db, [order.id])
    return _enrich_orders([order], ship_map)[0]


@router.put("/{order_id}/link-shipment")
async def link_shipment_to_order(
    order_id: int,
    payload:  dict,
    current_user: UserRead    = Depends(get_current_user),
    db:           AsyncSession = Depends(get_db),
):
    """Link or unlink a shipment to a production order.
    payload: {"shipment_id": <int>} to link, {"shipment_id": null} to unlink.
    """
    from sqlalchemy import update as sql_update
    result = await db.execute(
        select(ProductionOrder).where(
            ProductionOrder.id == order_id,
            ProductionOrder.org_id == current_user.org_id
        )
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Unlink any shipment currently pointing at this order
    await db.execute(
        sql_update(Shipment)
        .where(Shipment.order_id == order_id, Shipment.org_id == current_user.org_id)
        .values(order_id=None)
    )

    shipment_id = payload.get("shipment_id")
    if shipment_id:
        ship_res = await db.execute(
            select(Shipment).where(
                Shipment.id == shipment_id,
                Shipment.org_id == current_user.org_id
            )
        )
        shipment = ship_res.scalar_one_or_none()
        if not shipment:
            raise HTTPException(status_code=404, detail="Shipment not found")
        shipment.order_id = order_id

    await db.commit()
    await db.refresh(order)
    ship_map = await _load_shipment_map(db, [order_id])
    return _enrich_orders([order], ship_map)[0]


@router.delete("/{order_id}", status_code=204)
async def delete_order(
    order_id: int,
    current_user: UserRead    = Depends(get_current_user),
    db:           AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ProductionOrder).where(
            ProductionOrder.id == order_id,
            ProductionOrder.org_id == current_user.org_id
        )
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    await db.delete(order)
    await db.commit()
