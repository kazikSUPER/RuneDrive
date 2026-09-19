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
    "/portal",
    summary="Кабінет ріпердока / продавця модифікацій (тільки RIPPERDOC або ADMIN)",
)
async def get_vendor_portal(
    current_user: Annotated[
        User, Depends(require_roles(UserRole.RIPPERDOC, UserRole.ADMIN))
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Особистий кабінет продавця (ріпердока) з відображенням власних товарів."""
    my_items_count = (
        await db.execute(
            select(func.count())
            .select_from(Item)
            .where(Item.owner_id == current_user.id)
        )
    ).scalar() or 0

    return {
        "portal": "Ripperdoc Cyber-Workshop",
        "vendor": current_user.username,
        "role": current_user.role.value,
        "my_active_modifications": my_items_count,
        "clinic_status": "OPEN_FOR_IMPLANTATION",
    }
