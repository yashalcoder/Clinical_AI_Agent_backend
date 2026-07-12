from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import date
from typing import Optional, List

from app.database import get_db
from app.models.user import User
from app.schemas.doctor import DoctorUpdate, DoctorResponse
from app.core.security import (
    get_current_user,
    get_current_doctor,
    get_current_admin
)
from app.services.doctor_service import (
    get_doctor_by_user_id,
    get_doctor_by_id,
    get_all_doctors,
    get_available_slots,
    update_doctor_profile
)

router = APIRouter()


# ── GET /api/doctors/ ───────────────────────────────────────
@router.get("/")
def list_doctors(
    specialization: Optional[str] = Query(None, description="Filter by specialization"),
    db:             Session        = Depends(get_db),
    current_user:   User           = Depends(get_current_user)
):
    """
    Sab doctors ki list
    Patient appointment book karne se pehle yeh dekhe
    Filter: ?specialization=Dermatologist
    """
    return get_all_doctors(db, specialization=specialization)


# ── GET /api/doctors/me ─────────────────────────────────────
@router.get("/me", response_model=DoctorResponse)
def get_my_profile(
    current_user: User    = Depends(get_current_doctor),
    db:           Session = Depends(get_db)
):
    """Doctor apna profile dekhe"""
    return get_doctor_by_user_id(current_user.id, db)


# ── PUT /api/doctors/me ─────────────────────────────────────
@router.put("/me", response_model=DoctorResponse)
def update_my_profile(
    payload:      DoctorUpdate,
    current_user: User    = Depends(get_current_doctor),
    db:           Session = Depends(get_db)
):
    """
    Doctor apna profile update kare
    Schedule · fees · available days · slot duration
    """
    doctor = get_doctor_by_user_id(current_user.id, db)
    return update_doctor_profile(doctor.id, payload, db)


# ── GET /api/doctors/{doctor_id}/slots ──────────────────────
@router.get("/{doctor_id}/slots")
def available_slots(
    doctor_id:    UUID,
    date:         date    = Query(..., description="Format: 2024-12-25"),
    current_user: User    = Depends(get_current_user),
    db:           Session = Depends(get_db)
):
    """
    Kisi doctor ke available slots dekho specific date pe
    Patient appointment book karne se pehle yeh call kare

    Returns: ["09:00", "09:30", "10:00", ...]
    """
    slots = get_available_slots(doctor_id, date, db)
    return {
        "doctor_id":  doctor_id,
        "date":       date,
        "available_slots": slots,
        "total":      len(slots)
    }


# ── GET /api/doctors/{doctor_id} ────────────────────────────
@router.get("/{doctor_id}", response_model=DoctorResponse)
def get_doctor(
    doctor_id:    UUID,
    current_user: User    = Depends(get_current_user),
    db:           Session = Depends(get_db)
):
    """Specific doctor ki detail"""
    return get_doctor_by_id(doctor_id, db)


# ── PUT /api/doctors/{doctor_id} ────────────────────────────
@router.put("/{doctor_id}", response_model=DoctorResponse)
def update_doctor(
    doctor_id:    UUID,
    payload:      DoctorUpdate,
    current_user: User    = Depends(get_current_admin),
    db:           Session = Depends(get_db)
):
    """Admin kisi bhi doctor ka profile update kare"""
    return update_doctor_profile(doctor_id, payload, db)


# ── DELETE /api/doctors/{doctor_id} ─────────────────────────
@router.delete("/{doctor_id}")
def deactivate_doctor(
    doctor_id:    UUID,
    current_user: User    = Depends(get_current_admin),
    db:           Session = Depends(get_db)
):
    """
    Doctor ko deactivate karo (delete nahi — data rehta hai)
    Sirf Admin kar sakta hai
    """
    doctor = get_doctor_by_id(doctor_id, db)
    doctor.is_active = False
    db.commit()
    return {"message": "Doctor deactivated successfully"}