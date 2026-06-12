from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.database import get_db
from app.models.production import ProductionOrder
from pydantic import BaseModel
from app.models.notification import Notification

router = APIRouter(prefix="/production", tags=["Production"])


class ProductionCreate(BaseModel):
    order_no: str
    buyer: str
    style: str
    quantity: int


class StatusUpdate(BaseModel):
    status: str


VALID_STATUSES = [
    "Pending",
    "Cutting",
    "Sewing",
    "Finishing",
    "Packing",
    "Completed",
    "Cancelled"
]


@router.post("/create")
async def create_order(
    data: ProductionCreate,
    db: AsyncSession = Depends(get_db)
):
    order = ProductionOrder(
        order_no=data.order_no,
        buyer=data.buyer,
        style=data.style,
        quantity=data.quantity,
        status="Pending"
    )

    db.add(order)
    await db.commit()

    return {
        "message": "Production order created"
    }


@router.get("/all")
async def get_orders(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ProductionOrder).order_by(ProductionOrder.id.desc())
    )

    orders = result.scalars().all()

    return orders


@router.put("/status/{order_id}")
async def update_order_status(
    order_id: int,
    data: StatusUpdate,
    db: AsyncSession = Depends(get_db)
):
    if data.status not in VALID_STATUSES:
        return {
            "error": "Invalid status"
        }

    await db.execute(
        update(ProductionOrder)
        .where(ProductionOrder.id == order_id)
        .values(status=data.status)
    )

    order_result = await db.execute(
        select(ProductionOrder)
        .where(ProductionOrder.id == order_id)
    )

    order = order_result.scalar_one()

    notification = Notification(
        message=f"Production Order {order.order_no} changed to {data.status}",
        type="production"
    )

    db.add(notification)

    await db.commit()

    return {
        "message": "Status updated"
    }