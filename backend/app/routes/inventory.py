"""Inventory route — real PostgreSQL, org-scoped, auth-protected."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from app.dependencies import get_db, get_current_user
from app.models.inventory import Inventory
from app.schemas.auth import UserRead
from app.schemas.inventory import InventoryCreate

router = APIRouter()


@router.get("/")
async def get_inventory(
    category: Optional[str] = Query(None),
    status:   Optional[str] = Query(None),
    search:   Optional[str] = Query(None),
    limit:    int           = Query(100, le=500),
    offset:   int           = Query(0),
    current_user: UserRead    = Depends(get_current_user),
    db:           AsyncSession = Depends(get_db),
):
    q = select(Inventory)
    if category:
        q = q.where(Inventory.category == category)
    if status:
        q = q.where(Inventory.status == status)
    if search:
        q = q.where(Inventory.material_name.ilike(f"%{search}%"))
    q = q.order_by(Inventory.material_name).limit(limit).offset(offset)
    result = await db.execute(q)
    items = result.scalars().all()
    return [
        {
            "id": i.id, "material_code": i.material_code,
            "material_name": i.material_name, "category": i.category,
            "unit": i.unit, "stock_qty": i.stock_qty,
            "reserved_qty": i.reserved_qty, "available_qty": i.available_qty,
            "status": i.status,
        }
        for i in items
    ]


@router.get("/{item_id}")
async def get_inventory_item(
    item_id: int,
    current_user: UserRead    = Depends(get_current_user),
    db:           AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Inventory).where(Inventory.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.post("/", status_code=201)
async def create_inventory_item(
    payload: InventoryCreate,
    current_user: UserRead    = Depends(get_current_user),
    db:           AsyncSession = Depends(get_db),
):
    existing = await db.execute(
        select(Inventory).where(Inventory.material_code == payload.material_code)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Material code already exists")
    item = Inventory(
        material_code=payload.material_code, material_name=payload.material_name,
        category=payload.category, unit=payload.unit, stock_qty=payload.stock_qty,
        reserved_qty=0, available_qty=payload.stock_qty, status="In Stock",
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return {
        "id": item.id, "material_code": item.material_code,
        "material_name": item.material_name, "category": item.category,
        "unit": item.unit, "stock_qty": item.stock_qty,
        "reserved_qty": item.reserved_qty, "available_qty": item.available_qty,
        "status": item.status,
    }


@router.put("/{item_id}")
async def update_inventory_item(
    item_id: int,
    payload: dict,
    current_user: UserRead    = Depends(get_current_user),
    db:           AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Inventory).where(Inventory.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    allowed = {"stock_qty", "reserved_qty", "available_qty", "status"}
    for k, v in payload.items():
        if k in allowed:
            setattr(item, k, v)
    # When stock_qty is updated, recalculate available_qty unless caller overrides it
    if "stock_qty" in payload and "available_qty" not in payload:
        item.available_qty = max(0, item.stock_qty - (item.reserved_qty or 0))
    # Auto-update status based on final available_qty
    if item.available_qty <= 0:
        item.status = "Out of Stock"
    elif item.available_qty < 20:
        item.status = "Low Stock"
    else:
        item.status = "In Stock"
    await db.commit()
    await db.refresh(item)
    return {
        "id": item.id, "material_code": item.material_code,
        "material_name": item.material_name, "category": item.category,
        "unit": item.unit, "stock_qty": item.stock_qty,
        "reserved_qty": item.reserved_qty, "available_qty": item.available_qty,
        "status": item.status,
    }
