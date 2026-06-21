from pydantic import BaseModel
from uuid import UUID
from datetime import date, time, datetime
from typing import Optional
from app.models.appointment import AppointmentStatus, BookingChannel

# Appointment book karne ke liye
class AppointmentCreate(BaseModel):
    doctor_id:        UUID
    appointment_date: date
    slot_time:        time
    reason:           Optional[str] = None
    booked_via:       BookingChannel = BookingChannel.web

# Status update
class AppointmentUpdate(BaseModel):
    status: AppointmentStatus
    notes:  Optional[str] = None

# Response
class AppointmentResponse(BaseModel):
    id:               UUID
    patient_id:       UUID
    doctor_id:        UUID
    appointment_date: date
    slot_time:        time
    status:           AppointmentStatus
    reason:           Optional[str]
    notes:            Optional[str]
    booked_via:       BookingChannel
    created_at:       datetime

    class Config:
        from_attributes = True