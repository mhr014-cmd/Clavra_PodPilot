from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.inventory import Inventory

router = APIRouter(
    prefix="/analytics",
    tags=["Inventory Analytics"]
)


@router.get("/inventory")
async def inventory_analytics(
    db: AsyncSession = Depends(get_db)
):

    result = await db.execute(
        select(Inventory)
    )

    items = result.scalars().all()

    total_materials = len(items)

    total_stock = sum([
        item.stock_qty or 0
        for item in items
    ])

    low_stock = len([
        item for item in items
        if (item.stock_qty or 0) < 20
    ])

    out_of_stock = len([
        item for item in items
        if (item.stock_qty or 0) <= 0
    ])

    inventory_value = sum([
        (item.stock_qty or 0) * 10
        for item in items
    ])

    available_stock = sum([
        item.available_qty or 0
        for item in items
    ])

    return {
        "total_materials": total_materials,
        "total_stock": total_stock,
        "available_stock": available_stock,
        "low_stock": low_stock,
        "out_of_stock": out_of_stock,
        "inventory_value": inventory_value
    }