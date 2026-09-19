import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import UserRole


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, examples=["cyber_samurai"])
    email: EmailStr = Field(..., examples=["samurai@runedrive.net"])
    role: UserRole = Field(default=UserRole.BUYER, examples=[UserRole.BUYER])


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, examples=["cyber_samurai"])
    email: EmailStr = Field(..., examples=["samurai@runedrive.net"])
    password: str = Field(
        ..., min_length=6, max_length=128, examples=["SecurePass123!"]
    )
    role: UserRole = Field(default=UserRole.BUYER, examples=[UserRole.BUYER])


class UserUpdate(BaseModel):
    username: str | None = Field(None, min_length=3, max_length=50)
    email: EmailStr | None = None
    password: str | None = Field(None, min_length=6, max_length=128)


class UserResponse(UserBase):
    id: uuid.UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    username: str = Field(..., examples=["cyber_samurai"])
    password: str = Field(..., examples=["SecurePass123!"])


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user_id: uuid.UUID
