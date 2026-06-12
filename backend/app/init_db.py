from app.database import engine, Base

from app.models.user import User
from app.models.production import ProductionOrder


async def init_models():

    async with engine.begin() as conn:

        await conn.run_sync(
            Base.metadata.create_all
        )