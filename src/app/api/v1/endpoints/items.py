import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, require_roles
from app.core.database import get_db
from app.models.item import Item
from app.models.user import User, UserRole
from app.schemas.item import ItemCreate, ItemResponse, ItemUpdate

router = APIRouter()


@router.get(
    "/",
    response_model=list[ItemResponse],
    summary="Отримати список товарів каталогу (Публічний доступ)",
)
async def get_items(
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = 0,
    limit: int = 20,
) -> list[Item]:
    result = await db.execute(select(Item).offset(skip).limit(limit))
    return list(result.scalars().all())


@router.post(
    "/",
    response_model=ItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Створити нову модифікацію / товар (тільки RIPPERDOC або ADMIN)",
)
async def create_item(
    item_in: ItemCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        User, Depends(require_roles(UserRole.RIPPERDOC, UserRole.ADMIN))
    ],
) -> Item:
    existing = await db.execute(select(Item).where(Item.slug == item_in.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Item with this slug already exists",
        )

    item_data = item_in.model_dump()
    item_data["owner_id"] = current_user.id
    item = Item(**item_data)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


@router.get(
    "/{item_id}",
    response_model=ItemResponse,
    summary="Отримати товар за ідентифікатором",
)
async def get_item(
    item_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Item:
    item = await db.get(Item, item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found",
        )
    return item


@router.patch(
    "/{item_id}",
    response_model=ItemResponse,
    summary="Оновити товар (з IDOR-перевіркою прав власності)",
)
async def update_item(
    item_id: uuid.UUID,
    item_update: ItemUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> Item:
    """Оновлення товару із захистом від IDOR.

    Редагувати товар може лише той ріпердок, який його створив (власник), або ADMIN.
    Спроба іншого користувача змінити чужий товар повертає 403 Forbidden.
    """
    item = await db.get(Item, item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found",
        )

    if (
        item.owner_id is not None
        and item.owner_id != current_user.id
        and current_user.role != UserRole.ADMIN
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ заборонено: лише власник товару або адміністратор може змінювати цей запис (IDOR захист)",
        )

    update_data = item_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)

    await db.commit()
    await db.refresh(item)
    return item


@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Видалити товар (з IDOR-перевіркою)",
)
async def delete_item(
    item_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> None:
    item = await db.get(Item, item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found",
        )

    if (
        item.owner_id is not None
        and item.owner_id != current_user.id
        and current_user.role != UserRole.ADMIN
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ заборонено: лише власник товару або адміністратор може видалити цей запис (IDOR захист)",
        )

    await db.delete(item)
    await db.commit()
