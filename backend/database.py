
import os
from collections.abc import AsyncGenerator
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

load_dotenv()

USER = os.getenv("user")
PASSWORD = os.getenv("password")
HOST = os.getenv("host")
PORT = os.getenv("port", "5432")
DBNAME = os.getenv("dbname", "postgres")

if not all([USER, PASSWORD, HOST, PORT, DBNAME]):
    raise RuntimeError(
        "Missing Supabase database settings in backend/.env"
    )

DATABASE_URL = (
    f"postgresql+asyncpg://{quote_plus(USER)}:{quote_plus(PASSWORD)}"
    f"@{HOST}:{PORT}/{DBNAME}?ssl=require"
)

engine = create_async_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

class Base(DeclarativeBase):
    pass

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
