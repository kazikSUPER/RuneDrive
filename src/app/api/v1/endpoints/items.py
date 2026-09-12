import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.item import Item
from app.schemas.item import ItemCreate, ItemResponse

router = APIRouter()


@router.get(
    "/",
    response_model=list[ItemResponse],
    summary="Отримати список товарів каталогу",
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
    summary="Створити нову модифікацію / товар",
)
async def create_item(
    item_in: ItemCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Item:
    existing = await db.execute(select(Item).where(Item.slug == item_in.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Item with this slug already exists",
        )

    item = Item(**item_in.model_dump())
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
