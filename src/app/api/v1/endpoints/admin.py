from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_roles
from app.core.database import get_db
from app.models.item import Item
from app.models.user import User, UserRole

router = APIRouter()


@router.get(
    "/dashboard",
    summary="Панель керування адміністратора платформи (Vertical RBAC: тільки ADMIN)",
)
async def get_admin_dashboard(
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Ендпоінт адміністратора з вертикальним контролем доступу (RBAC).

    Доступ дозволено виключно користувачам із роллю ADMIN.
    Будь-яка інша роль (BUYER, RIPPERDOC) отримує 403 Forbidden.
    """
    users_count = (
        await db.execute(select(func.count()).select_from(User))
    ).scalar() or 0
    items_count = (
        await db.execute(select(func.count()).select_from(Item))
    ).scalar() or 0

    return {
        "panel": "RuneDrive Cyber-Command Center",
        "admin_user": current_user.username,
        "role": current_user.role.value,
        "system_status": "OPERATIONAL",
        "metrics": {
            "registered_users": users_count,
            "marketplace_items": items_count,
            "security_mode": "STRICT_RBAC_ENABLED",
        },
    }
