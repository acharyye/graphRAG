"""Pydantic models for authentication."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, EmailStr, Field


class UserRole(str, Enum):
    """User roles in the system."""

    ADMIN = "admin"
    ANALYST = "analyst"
    MANAGER = "manager"
    EXECUTIVE = "executive"


class LoginRequest(BaseModel):
    """Login request model."""

    email: EmailStr
    password: str = Field(..., min_length=8)


class LoginResponse(BaseModel):
    """Login response model."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Token expiration in seconds")
    user: "UserResponse"


class UserBase(BaseModel):
    """Base user model."""

    email: EmailStr
    name: str = Field(..., min_length=1, max_length=255)
    role: UserRole = UserRole.MANAGER


class UserCreate(UserBase):
    """User creation model."""

    password: str = Field(..., min_length=8)
    client_ids: list[str] = Field(default_factory=list)


class UserUpdate(BaseModel):
    """User update model."""

    name: str | None = Field(None, min_length=1, max_length=255)
    role: UserRole | None = None
    client_ids: list[str] | None = None


class UserResponse(UserBase):
    """User response model."""

    id: str
    client_ids: list[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TokenPayload(BaseModel):
    """JWT token payload."""

    sub: str  # User ID
    email: str
    role: UserRole
    client_ids: list[str]
    exp: datetime


class PasswordChangeRequest(BaseModel):
    """Password change request."""

    current_password: str = Field(..., min_length=8)
    new_password: str = Field(..., min_length=8)


# Fix forward reference
LoginResponse.model_rebuild()
