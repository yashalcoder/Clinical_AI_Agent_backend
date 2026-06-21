import uuid
import enum
from sqlalchemy import Column, String, Date, Time, DateTime, ForeignKey, UniqueConstraint, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class AppointmentStatus(str, enum.Enum):
    pending   = "pending"
    confirmed = "confirmed"
    cancelled = "cancelled"
    completed = "completed"
    no_show   = "no_show"

class BookingChannel(str, enum.Enum):
    whatsapp = "whatsapp"
    call     = "call"
    web      = "web"

class Appointment(Base):
    __tablename__ = "appointments"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id       = Column(UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    doctor_id        = Column(UUID(as_uuid=True), ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False)
    appointment_date = Column(Date, nullable=False)
    slot_time        = Column(Time, nullable=False)
    status           = Column(SAEnum(AppointmentStatus), default=AppointmentStatus.pending)
    reason           = Column(String)
    notes            = Column(String)
    booked_via       = Column(SAEnum(BookingChannel), default=BookingChannel.web)
    created_at       = Column(DateTime(timezone=True), server_default=func.now())
    updated_at       = Column(DateTime(timezone=True), onupdate=func.now())

    # Prevent double booking
    __table_args__ = (
        UniqueConstraint("doctor_id", "appointment_date", "slot_time", name="uq_doctor_slot"),
    )

    # Relationships
    reminders = relationship("Reminder", backref="appointment")
    record    = relationship("MedicalRecord", backref="appointment", uselist=False)