from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db

router = APIRouter()


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Базовий Healthcheck",
)
async def health_check() -> dict[str, str]:
    """Перевірка життєдіяльності застосунку (Liveness probe)."""
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
    }


@router.get(
    "/ready",
    status_code=status.HTTP_200_OK,
    summary="Readiness probe з перевіркою підключення до PostgreSQL",
)
async def readiness_check(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    """Перевірка готовності застосунку та доступності бази даних (Readiness probe)."""
    try:
        await db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"unavailable: {e}"

    return {
        "status": "ready" if "connected" in db_status else "degraded",
        "database": db_status,
    }
