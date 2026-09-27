from pydantic import BaseModel
from uuid import UUID
from datetime import date, time, datetime
from typing import Optional

from app.models.appointment import AppointmentStatus, BookingChannel


class AppointmentCreate(BaseModel):
    doctor_id: UUID
    appointment_date: date
    slot_time: time
    reason: Optional[str] = None
    booked_via: BookingChannel = BookingChannel.web


class AppointmentUpdate(BaseModel):
    status: AppointmentStatus
    notes: Optional[str] = None


class UserResponse(BaseModel):
    full_name: str

    class Config:
        from_attributes = True


class DoctorResponse(BaseModel):
    id: UUID
    specialization: str
    qualification: Optional[str] = None
    user: UserResponse

    class Config:
        from_attributes = True


class AppointmentResponse(BaseModel):
    id: UUID
    patient_id: UUID
    doctor_id: UUID
    appointment_date: date
    slot_time: time
    status: AppointmentStatus
    reason: Optional[str] = None
    notes: Optional[str] = None
    booked_via: BookingChannel
    created_at: datetime
    doctor: DoctorResponse

    class Config:
        from_attributes = True
