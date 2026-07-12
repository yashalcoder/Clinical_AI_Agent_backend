from pydantic import BaseModel, EmailStr
from uuid import UUID
from typing import Optional
from app.models.user import UserRole


class RegisterRequest(BaseModel):
    email:     EmailStr
    full_name: str
    phone:     str
    password:  str
    role:      UserRole


class LoginRequest(BaseModel):
    email:    EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token:  str
    token_type:    str = "bearer"
    role:          UserRole
    user_id:       UUID
    full_name:     str
    picture:       Optional[str] = None
    is_new_user:   bool = False    # Google se pehli baar aaya? Frontend role screen dikhaye


class UserResponse(BaseModel):
    id:            UUID
    email:         str
    full_name:     str
    phone:         Optional[str]
    role:          UserRole
    picture:       Optional[str]
    auth_provider: str
    is_active:     bool

    class Config:
        from_attributes = True


class UpdateRoleRequest(BaseModel):
    """Pehli baar Google login ke baad role select karne ke liye"""
    role: UserRole