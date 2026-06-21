import uuid
from sqlalchemy import Column, String, Date, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.database import Base

class MedicalRecord(Base):
    __tablename__ = "medical_records"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    appointment_id = Column(UUID(as_uuid=True), ForeignKey("appointments.id", ondelete="SET NULL"), nullable=True)
    patient_id     = Column(UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    doctor_id      = Column(UUID(as_uuid=True), ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False)
    symptoms       = Column(Text)
    diagnosis      = Column(Text)
    prescriptions  = Column(JSONB, default=[])
    # prescriptions format:
    # [{"medicine": "Panadol", "dosage": "500mg", "times": "2x daily", "days": 5}]
    voice_note_url = Column(String)   # Whisper converted file URL
    follow_up_date = Column(Date)
    created_at     = Column(DateTime(timezone=True), server_default=func.now())
    updated_at     = Column(DateTime(timezone=True), onupdate=func.now())