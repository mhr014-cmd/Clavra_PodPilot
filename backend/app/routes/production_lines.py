"""Production Lines route — org-scoped, auth-protected, with order enrichment."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from app.dependencies import get_db, get_current_user
from app.models.production_line import ProductionLine
from app.models.production import ProductionOrder
from app.schemas.auth import UserRead
from app.schemas.production_line import ProductionLineCreate

router = APIRouter()

ACTIVE_STATUSES = ("Pending", "Cutting", "Sewing", "Finishing", "Packing")


async def _load_line_orders(db: AsyncSession, line_ids: list[int], org_id: int | None = None) -> dict:
    """Return {line_id: [order_dict, ...]} for all active orders on each line.

    Note: ProductionLine has no org_id column — lines are global. We scope by
    org_id when provided, but fall back to line_id-only to avoid Optional[int]
    == None generating an IS NULL clause that excludes all real rows.
    """
    if not line_ids:
        return {}
    conditions = [
        ProductionOrder.line_id.in_(line_ids),
        ProductionOrder.status.in_(ACTIVE_STATUSES),
    ]
    if org_id is not None:
        conditions.append(ProductionOrder.org_id == org_id)
    result = await db.execute(
        select(ProductionOrder)
        .where(*conditions)
        .order_by(ProductionOrder.id.desc())
    )
    orders = result.scalars().all()
    line_map: dict[int, list] = {}
    for o in orders:
        pct = round((o.produced_qty or 0) / max(o.quantity, 1) * 100)
        entry = {
            "id":           o.id,
            "order_no":     o.order_no,
            "buyer":        o.buyer,
            "style":        o.style,
            "status":       o.status,
            "quantity":     o.quantity,
            "produced_qty": o.produced_qty or 0,
            "progress_pct": pct,
        }
        line_map.setdefault(o.line_id, []).append(entry)
    return line_map


def _serialize_line(line: ProductionLine, orders: list) -> dict:
    return {
        "id":            line.id,
        "line_name":     line.line_name,
        "supervisor":    line.supervisor,
        "status":        line.status,
        "target_output": line.target_output,
        "actual_output": line.actual_output,
        "efficiency":    line.efficiency,
        "defects":       line.defects,
        "operators":     line.operators,
        "current_orders": orders,
    }


@router.get("/")
async def get_production_lines(
    current_user: UserRead    = Depends(get_current_user),
    db:           AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ProductionLine).order_by(ProductionLine.line_name)
    )
    lines = result.scalars().all()
    line_ids = [l.id for l in lines]
    order_map = await _load_line_orders(db, line_ids, current_user.org_id)
    return [_serialize_line(l, order_map.get(l.id, [])) for l in lines]


@router.get("/{line_id}")
async def get_line(
    line_id: int,
    current_user: UserRead    = Depends(get_current_user),
    db:           AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ProductionLine).where(ProductionLine.id == line_id))
    line = result.scalar_one_or_none()
    if not line:
        raise HTTPException(status_code=404, detail="Production line not found")
    order_map = await _load_line_orders(db, [line_id], current_user.org_id)
    return _serialize_line(line, order_map.get(line_id, []))


@router.post("/", status_code=201)
async def create_line(
    payload: ProductionLineCreate,
    current_user: UserRead    = Depends(get_current_user),
    db:           AsyncSession = Depends(get_db),
):
    line = ProductionLine(
        line_name=payload.line_name, supervisor=payload.supervisor,
        status="Running", target_output=payload.target_output,
        actual_output=0, efficiency=0, defects=0, operators=payload.operators,
    )
    db.add(line)
    await db.commit()
    await db.refresh(line)
    return _serialize_line(line, [])


@router.put("/{line_id}")
async def update_line(
    line_id: int,
    payload: dict,
    current_user: UserRead    = Depends(get_current_user),
    db:           AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ProductionLine).where(ProductionLine.id == line_id))
    line = result.scalar_one_or_none()
    if not line:
        raise HTTPException(status_code=404, detail="Production line not found")
    allowed = {"status", "actual_output", "efficiency", "defects", "supervisor", "operators", "target_output"}
    for k, v in payload.items():
        if k in allowed:
            setattr(line, k, v)
    await db.commit()
    await db.refresh(line)
    order_map = await _load_line_orders(db, [line_id], current_user.org_id)
    return _serialize_line(line, order_map.get(line_id, []))


@router.delete("/{line_id}", status_code=200)
async def delete_line(
    line_id: int,
    current_user: UserRead    = Depends(get_current_user),
    db:           AsyncSession = Depends(get_db),
):
    from sqlalchemy import text
    result = await db.execute(select(ProductionLine).where(ProductionLine.id == line_id))
    line = result.scalar_one_or_none()
    if not line:
        raise HTTPException(status_code=404, detail="Production line not found")
    # Unassign any orders currently on this line before deleting
    await db.execute(
        text("UPDATE production_orders SET line_id = NULL WHERE line_id = :lid"),
        {"lid": line_id},
    )
    await db.delete(line)
    await db.commit()
    return {"message": f"Production line '{line.line_name}' deleted"}
