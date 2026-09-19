from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.item import Item


class UserRole(StrEnum):
    """Ролі користувачів платформи RuneDrive."""

    BUYER = "BUYER"
    RIPPERDOC = "RIPPERDOC"
    ADMIN = "ADMIN"


class User(Base, TimestampMixin):
    """Модель користувача з рольовим доступом та UUID ключем."""

    __tablename__ = "users"

    username: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole, name="user_role_enum"),
        default=UserRole.BUYER,
        nullable=False,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    items: Mapped[list["Item"]] = relationship(
        "Item", back_populates="owner", cascade="all, delete-orphan"
    )
