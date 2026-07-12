from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import date
from typing import Optional

from app.database import get_db
from app.models.user import User
from app.schemas.appointment import (
    AppointmentCreate,
    AppointmentUpdate,
    AppointmentResponse
)
from app.core.security import (
    get_current_user,
    get_current_patient,
    get_current_doctor,
    get_current_admin
)
from app.services.appointment_service import (
    book_appointment,
    get_patient_appointments,
    get_doctor_appointments,
    get_appointment_by_id,
    update_appointment_status,
    reschedule_appointment,
    get_all_appointments
)

router = APIRouter()


# ── POST /api/appointments/ ─────────────────────────────────
@router.post("/", response_model=AppointmentResponse, status_code=201)
def book(
    payload:      AppointmentCreate,
    current_user: User    = Depends(get_current_patient),
    db:           Session = Depends(get_db)
):
    """
    Appointment book karo — sirf patient
    
    Body:
    {
        "doctor_id": "uuid",
        "appointment_date": "2024-12-25",
        "slot_time": "10:00",
        "reason": "Fever and headache",
        "booked_via": "web"
    }
    """
    return book_appointment(payload, current_user.id, db)


# ── GET /api/appointments/my ────────────────────────────────
@router.get("/my", response_model=list[AppointmentResponse])
def my_appointments(
    status:       Optional[str] = Query(None, description="pending|confirmed|cancelled|completed"),
    current_user: User          = Depends(get_current_patient),
    db:           Session       = Depends(get_db)
):
    """Patient apni sab appointments dekhe"""
    return get_patient_appointments(current_user.id, status, db)


# ── GET /api/appointments/doctor ────────────────────────────
@router.get("/doctor", response_model=list[AppointmentResponse])
def doctor_schedule(
    date:         Optional[date] = Query(None, description="Filter by date: 2024-12-25"),
    status:       Optional[str]  = Query(None),
    current_user: User           = Depends(get_current_doctor),
    db:           Session        = Depends(get_db)
):
    """
    Doctor apna schedule dekhe
    ?date=2024-12-25 → us din ki appointments
    """
    return get_doctor_appointments(current_user.id, date, status, db)


# ── GET /api/appointments/all ───────────────────────────────
@router.get("/all", response_model=list[AppointmentResponse])
def all_appointments(
    date:         Optional[date] = Query(None),
    status:       Optional[str]  = Query(None),
    doctor_id:    Optional[UUID] = Query(None),
    skip:         int            = Query(0, ge=0),
    limit:        int            = Query(50, le=100),
    current_user: User           = Depends(get_current_admin),
    db:           Session        = Depends(get_db)
):
    """Admin → sab appointments dekhe with filters"""
    return get_all_appointments(db, date, status, doctor_id, skip, limit)


# ── GET /api/appointments/{id} ──────────────────────────────
@router.get("/{appointment_id}", response_model=AppointmentResponse)
def get_appointment(
    appointment_id: UUID,
    current_user:   User    = Depends(get_current_user),
    db:             Session = Depends(get_db)
):
    """Single appointment detail"""
    appointment = get_appointment_by_id(appointment_id, db)

    # Access check
    if current_user.role == "patient":
        from app.models.patient import Patient
        patient = db.query(Patient).filter(
            Patient.user_id == current_user.id
        ).first()
        if appointment.patient_id != patient.id:
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="Access denied")

    elif current_user.role == "doctor":
        from app.models.doctor import Doctor
        doctor = db.query(Doctor).filter(
            Doctor.user_id == current_user.id
        ).first()
        if appointment.doctor_id != doctor.id:
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="Access denied")

    return appointment


# ── PATCH /api/appointments/{id}/status ─────────────────────
@router.patch("/{appointment_id}/status", response_model=AppointmentResponse)
def update_status(
    appointment_id: UUID,
    payload:        AppointmentUpdate,
    current_user:   User    = Depends(get_current_user),
    db:             Session = Depends(get_db)
):
    """
    Status update karo

    Patient  → cancel only
    Doctor   → confirm, complete, no_show
    Admin    → kuch bhi

    Body: { "status": "confirmed", "notes": "optional note" }
    """
    return update_appointment_status(
        appointment_id,
        payload,
        current_user.id,
        current_user.role,
        db
    )


# ── PATCH /api/appointments/{id}/reschedule ─────────────────
@router.patch("/{appointment_id}/reschedule", response_model=AppointmentResponse)
def reschedule(
    appointment_id: UUID,
    new_date:       date = Query(..., description="New date: 2024-12-25"),
    new_slot:       str  = Query(..., description="New time: 10:30"),
    current_user:   User    = Depends(get_current_patient),
    db:             Session = Depends(get_db)
):
    """
    Appointment reschedule karo — sirf patient
    Naya slot available hona chahiye
    """
    return reschedule_appointment(
        appointment_id,
        new_date,
        new_slot,
        current_user.id,
        db
    )


# ── DELETE /api/appointments/{id} ───────────────────────────
@router.delete("/{appointment_id}")
def cancel_appointment(
    appointment_id: UUID,
    current_user:   User    = Depends(get_current_user),
    db:             Session = Depends(get_db)
):
    """
    Appointment cancel karo
    Shortcut — status ko cancelled set karta hai
    """
    from app.schemas.appointment import AppointmentUpdate
    from app.models.appointment import AppointmentStatus

    payload = AppointmentUpdate(status=AppointmentStatus.cancelled)
    return update_appointment_status(
        appointment_id,
        payload,
        current_user.id,
        current_user.role,
        db
    )