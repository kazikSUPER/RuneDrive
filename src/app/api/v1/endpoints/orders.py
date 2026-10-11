import uuid
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.core.database import get_db
from app.models.item import Item
from app.models.order import Order, OrderItem, OrderStatus
from app.models.user import User
from app.schemas.order import OrderCreate, OrderRead

router = APIRouter()


@router.post(
    "/",
    response_model=OrderRead,
    status_code=status.HTTP_201_CREATED,
    summary="Створити нове замовлення модифікацій/артефактів",
)
async def create_order(
    order_in: OrderCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> Order:
    total_amount = Decimal("0.00")
    order_items_to_create: list[OrderItem] = []

    for item_req in order_in.items:
        res = await db.execute(select(Item).where(Item.id == item_req.item_id))
        item = res.scalar_one_or_none()

        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Товар з ID {item_req.item_id} не знайдено",
            )

        if not item.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Товар '{item.title}' наразі недоступний для замовлення",
            )

        if item.stock_quantity < item_req.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Недостатньо залишку товару '{item.title}' (наявно: {item.stock_quantity}, запитано: {item_req.quantity})",
            )

        item.stock_quantity -= item_req.quantity
        line_total = item.price * item_req.quantity
        total_amount += line_total

        order_item = OrderItem(
            item_id=item.id,
            quantity=item_req.quantity,
            unit_price=item.price,
        )
        order_items_to_create.append(order_item)

    new_order = Order(
        user_id=current_user.id,
        status=OrderStatus.PENDING,
        total_price=total_amount,
        delivery_point=order_in.delivery_point,
    )
    db.add(new_order)
    await db.flush()

    for oi in order_items_to_create:
        oi.order_id = new_order.id
        db.add(oi)

    await db.commit()
    await db.refresh(new_order)
    return new_order


@router.get(
    "/",
    response_model=list[OrderRead],
    summary="Отримати список усіх замовлень поточного користувача",
)
async def get_my_orders(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    skip: int = 0,
    limit: int = 20,
) -> list[Order]:
    query = (
        select(Order)
        .where(Order.user_id == current_user.id)
        .order_by(Order.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    return list(result.scalars().all())


@router.get(
    "/{order_id}",
    response_model=OrderRead,
    summary="Отримати деталі конкретного замовлення",
)
async def get_order_by_id(
    order_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> Order:
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Замовлення не знайдено",
        )

    if order.user_id != current_user.id and current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ заборонено (IDOR захист)",
        )

    return order


@router.put(
    "/{order_id}/cancel",
    response_model=OrderRead,
    summary="Скасувати замовлення та повернути залишки товару на склад",
)
async def cancel_order(
    order_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> Order:
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Замовлення не знайдено",
        )

    if order.user_id != current_user.id and current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ заборонено",
        )

    if order.status in [OrderStatus.COMPLETED, OrderStatus.CANCELLED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Неможливо скасувати замовлення в статусі {order.status}",
        )

    order.status = OrderStatus.CANCELLED

    for oi in order.items:
        res = await db.execute(select(Item).where(Item.id == oi.item_id))
        item = res.scalar_one_or_none()
        if item:
            item.stock_quantity += oi.quantity

    await db.commit()
    await db.refresh(order)
    return order
