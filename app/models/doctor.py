import uuid
from sqlalchemy import Column, String, Boolean, Integer, Numeric, Time, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Doctor(Base):
    __tablename__ = "doctors"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id         = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    specialization  = Column(String, nullable=False)
    qualification   = Column(String)
    fee             = Column(Numeric(10, 2), default=0)
    available_days  = Column(JSONB, default=["Mon", "Tue", "Wed", "Thu", "Fri"])
    slot_duration   = Column(Integer, default=30)   # minutes
    start_time      = Column(Time, default="09:00")
    end_time        = Column(Time, default="17:00")
    is_active       = Column(Boolean, default=True)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user         = relationship("User", backref="doctor")
    appointments = relationship("Appointment", backref="doctor")
    records      = relationship("MedicalRecord", backref="doctor")