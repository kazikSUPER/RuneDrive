import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.core.database import get_db
from app.core.security import get_password_hash
from app.models.user import User, UserRole
from app.schemas.user import UserResponse, UserUpdate

router = APIRouter()


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Отримання публічного профілю користувача",
)
async def get_user_by_id(
    user_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    """Отримання профілю за ID."""
    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Користувача не знайдено",
        )
    return user


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    summary="Оновлення профілю з перевіркою IDOR",
)
async def update_user_profile(
    user_id: uuid.UUID,
    user_update: UserUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    """Оновлення профілю з горизонтальним розмежуванням прав (захист від IDOR).

    Користувач має право редагувати виключно власний профіль.
    Спроба змінити чужий профіль повертає 403 Forbidden, якщо користувач не є ADMIN.
    """
    if current_user.id != user_id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ заборонено: спроба модифікації чужого профілю (IDOR захист)",
        )

    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    target_user = result.scalar_one_or_none()

    if target_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Користувача не знайдено",
        )

    if user_update.username is not None:
        target_user.username = user_update.username
    if user_update.email is not None:
        target_user.email = user_update.email
    if user_update.password is not None:
        target_user.hashed_password = get_password_hash(user_update.password)

    await db.commit()
    await db.refresh(target_user)
    return target_user
