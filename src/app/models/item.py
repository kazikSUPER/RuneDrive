from decimal import Decimal
from enum import StrEnum

from sqlalchemy import Boolean, Numeric, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin


class ItemCategory(StrEnum):
    IMPLANT = "IMPLANT"  # Апаратні модифікації (кібер-очі, хром, Сандевістан)
    SOFTWARE = "SOFTWARE"  # Цифрові руни, ліцензії на заклинання, прошивки
    ALCHEMY = "ALCHEMY"  # Зілля мани, біо-еліксири регенерації
    SERVICE = "SERVICE"  # Послуги підпільних ріпердоків


class Item(Base, TimestampMixin):
    """Модель товару маркетплейсу RuneDrive."""

    __tablename__ = "items"

    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    category: Mapped[ItemCategory] = mapped_column(
        SQLEnum(ItemCategory, name="item_category_enum"),
        nullable=False,
        index=True,
    )
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    stock_quantity: Mapped[int] = mapped_column(default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # JSONB дозволяє зберігати довільні характеристики (мана, слоти, сумісність)
    # без потреби змінювати схему реляційної БД
    specs: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
