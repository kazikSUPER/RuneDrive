import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.order import OrderStatus


class OrderItemCreate(BaseModel):
    """Схема додавання товару в замовлення."""

    item_id: uuid.UUID
    quantity: int = Field(default=1, ge=1, le=100)


class OrderItemRead(BaseModel):
    """Схема читання позиції замовлення."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    item_id: uuid.UUID
    quantity: int
    unit_price: Decimal


class OrderCreate(BaseModel):
    """Схема створення замовлення покупцем."""

    items: list[OrderItemCreate] = Field(min_length=1)
    delivery_point: str = Field(default="Night City Drop-Point #42", max_length=255)


class OrderRead(BaseModel):
    """Схема детального перегляду замовлення."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    status: OrderStatus
    total_price: Decimal
    delivery_point: str
    items: list[OrderItemRead]
    created_at: datetime
    updated_at: datetime


class OrderStatusUpdate(BaseModel):
    """Оновлення статусу замовлення."""

    status: OrderStatus
