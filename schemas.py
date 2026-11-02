# schemas.py
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime

# --- Схемы для пользователей ---
class UserCreate(BaseModel):
    username: str
    password: str

class UserUpdate(BaseModel):
    username: str | None = None
    password: str | None = None

class UserResponse(BaseModel):
    id: int
    username: str

    class Config:
        from_attributes = True

# --- Схемы для логина ---
class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    token: UUID

    class Config:
        from_attributes = True

# --- Схемы для объявлений ---
class AdCreate(BaseModel):
    title: str
    description: str
    price: float = Field(..., gt=0)

class AdUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    price: float | None = Field(None, gt=0)

class AdResponse(BaseModel):
    id: int
    title: str
    description: str
    price: float
    author_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class IdResponse(BaseModel):
    id: int