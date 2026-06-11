from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from app.models.inventory import Inventory


async def get_low_stock_items(db: AsyncSession, org_id: int, limit: int = 10) -> list:
    result = await db.execute(
        select(Inventory)
        .where(Inventory.status.in_(["Low Stock", "Critical", "Out of Stock"]))
        .order_by(Inventory.available_qty.asc())
        .limit(min(limit, 50))
    )
    items = result.scalars().all()
    if not items:
        result2 = await db.execute(
            select(Inventory).order_by(Inventory.available_qty.asc()).limit(min(limit, 50))
        )
        items = result2.scalars().all()
    return [{"material_code": i.material_code, "material_name": i.material_name,
             "available_qty": i.available_qty, "unit": i.unit, "status": i.status} for i in items]


async def check_inventory(db: AsyncSession, item_ref: str, org_id: int) -> dict | None:
    result = await db.execute(
        select(Inventory).where(
            or_(
                Inventory.material_code.ilike(f"%{item_ref}%"),
                Inventory.material_name.ilike(f"%{item_ref}%"),
            )
        ).limit(1)
    )
    item = result.scalar_one_or_none()
    if not item:
        return None
    return {"id": item.id, "material_code": item.material_code,
            "material_name": item.material_name, "category": item.category,
            "unit": item.unit, "stock_qty": item.stock_qty,
            "available_qty": item.available_qty, "status": item.status}
