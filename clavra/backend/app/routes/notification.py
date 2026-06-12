from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.notification import Notification

router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"]
)


@router.get("/")
async def get_notifications(
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Notification)
        .order_by(Notification.id.desc())
    )

    notifications = result.scalars().all()

    return notifications