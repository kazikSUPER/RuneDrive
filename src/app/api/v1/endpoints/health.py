from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db

import asyncio
import os
import socket

router = APIRouter()
INSTANCE_ID = os.getenv("INSTANCE_ID", socket.gethostname())


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Базовий Healthcheck",
)
async def health_check() -> dict[str, str]:
    """Перевірка життєдіяльності застосунку (Liveness probe) з ідентифікатором інстансу."""
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "instance_id": INSTANCE_ID,
    }


@router.get(
    "/health/delayed",
    status_code=status.HTTP_200_OK,
    summary="Емуляція штучної затримки для тестування Least Connections",
)
async def delayed_health_check(delay_ms: int = 150) -> dict[str, any]:
    """Емуляція асиметричного навантаження/затримки для Лаб 3."""
    await asyncio.sleep(delay_ms / 1000.0)
    return {
        "status": "delayed_ok",
        "delay_ms": delay_ms,
        "instance_id": INSTANCE_ID,
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
