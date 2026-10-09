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
    email:str
    phone: Optional[str] = None
    class Config:
        from_attributes = True


class DoctorResponse(BaseModel):
    id: UUID
    specialization: str
    qualification: Optional[str] = None
    user: UserResponse

    class Config:
        from_attributes = True

class PatientResponse(BaseModel):
    id: UUID
    whatsapp_no: Optional[str] = None
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
    patient:PatientResponse

    class Config:
        from_attributes = True
class AdminAppointmentEditSchema(BaseModel):
    # Patient Info
    patient_full_name: Optional[str] = None
    contact_number: Optional[str] = None
    whatsapp_number: Optional[str] = None
    email: Optional[str] = None

    # Visit Info
    reason: Optional[str] = None
    notes: Optional[str] = None

    # Doctor & Schedule
    doctor_id: Optional[UUID] = None
    appointment_date: Optional[date] = None
    slot_time: Optional[time] = None