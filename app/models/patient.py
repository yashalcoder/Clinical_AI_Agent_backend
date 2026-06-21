import uuid
from sqlalchemy import Column, String, Date, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Patient(Base):
    __tablename__ = "patients"

    id                      = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id                 = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    date_of_birth           = Column(Date)
    gender                  = Column(String)
    blood_group             = Column(String)
    whatsapp_no             = Column(String)
    address                 = Column(String)
    emergency_contact_name  = Column(String)
    emergency_contact_phone = Column(String)
    created_at              = Column(DateTime(timezone=True), server_default=func.now())
    updated_at              = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user         = relationship("User", backref="patient")
    appointments = relationship("Appointment", backref="patient")
    records      = relationship("MedicalRecord", backref="patient")