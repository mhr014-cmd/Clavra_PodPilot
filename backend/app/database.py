from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker
)

from sqlalchemy.orm import declarative_base

from dotenv import load_dotenv

import os


# LOAD ENV VARIABLES
load_dotenv()


# DATABASE URL
DATABASE_URL = os.getenv(
    "DATABASE_URL"
)


# ASYNC ENGINE
engine = create_async_engine(
    DATABASE_URL,
    echo=True
)


# ASYNC SESSION
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)


# BASE MODEL
Base = declarative_base()


# DATABASE DEPENDENCY
async def get_db():

    async with AsyncSessionLocal() as session:
        yield session