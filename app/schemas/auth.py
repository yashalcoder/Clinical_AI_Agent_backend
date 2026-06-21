from pydantic import BaseModel, EmailStr
from uuid import UUID
from app.models.user import UserRole

# Register karne ke liye
class RegisterRequest(BaseModel):
    email:     EmailStr
    full_name: str
    phone:     str
    password:  str
    role:      UserRole

# Login karne ke liye
class LoginRequest(BaseModel):
    email:    EmailStr
    password: str

# Token response
class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    role:         UserRole
    user_id:      UUID
    full_name:    str

# User info response
class UserResponse(BaseModel):
    id:        UUID
    email:     str
    full_name: str
    phone:     str | None
    role:      UserRole
    is_active: bool

    class Config:
        from_attributes = True