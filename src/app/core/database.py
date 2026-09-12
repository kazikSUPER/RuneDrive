from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# Створення асинхронного рушія бази даних
engine = create_async_engine(
    settings.async_database_url,
    echo=False,
    future=True,
    pool_pre_ping=True,
)

# Фабрика асинхронних сесій
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Базовий декларативний клас для всіх моделей проєкту."""

    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency для отримання асинхронної сесії БД у FastAPI ендпоінтах."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
