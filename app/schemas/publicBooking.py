from datetime import date, time
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr

class PublicAppointmentCreate(BaseModel):
    clinic_id: int

    full_name: str
    email: EmailStr
    whatsapp_no: str
    contact_no: Optional[str] = None

    doctor_id: UUID
    appointment_date: date
    slot_time: time
    reason: Optional[str] = None