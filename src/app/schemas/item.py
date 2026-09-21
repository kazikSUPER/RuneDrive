import uuid
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.item import ItemCategory


class ItemBase(BaseModel):
    title: str = Field(..., max_length=255, examples=["Очний імплант «Кіроші Mk.3»"])
    slug: str = Field(..., max_length=255, examples=["kiroshi-optics-mk3"])
    category: ItemCategory = Field(..., examples=[ItemCategory.IMPLANT])
    price: Decimal = Field(..., ge=0, examples=[1500.00])
    stock_quantity: int = Field(default=0, ge=0, examples=[25])
    is_active: bool = True
    specs: dict[str, Any] = Field(
        default_factory=dict, examples=[{"zoom": "8x", "scan_speed": "0.2s"}]
    )


class ItemCreate(ItemBase):
    pass


class ItemUpdate(BaseModel):
    title: str | None = None
    price: Decimal | None = None
    stock_quantity: int | None = None
    is_active: bool | None = None
    specs: dict[str, Any] | None = None


class ItemResponse(ItemBase):
    id: uuid.UUID
    owner_id: uuid.UUID | None = None

    model_config = ConfigDict(from_attributes=True)
