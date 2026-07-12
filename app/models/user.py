import uuid
import enum
from sqlalchemy import Column, String, Boolean, DateTime, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.database import Base


class UserRole(str, enum.Enum):
    admin   = "admin"
    doctor  = "doctor"
    patient = "patient"


class User(Base):
    __tablename__ = "users"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email       = Column(String, unique=True, nullable=False)
    full_name   = Column(String, nullable=False)
    phone       = Column(String)
    role        = Column(SAEnum(UserRole), nullable=False)
    password    = Column(String, nullable=True)   # Google login pe NULL hoga
    google_id   = Column(String, unique=True, nullable=True)  # Google ka ID
    picture     = Column(String, nullable=True)   # Profile photo
    auth_provider = Column(String, default="email")  # "email" ya "google"
    is_active   = Column(Boolean, default=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    updated_at  = Column(DateTime(timezone=True), onupdate=func.now())