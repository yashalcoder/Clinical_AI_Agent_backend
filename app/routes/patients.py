from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional

from app.database import get_db
from app.models.user import User
from app.schemas.patient import PatientUpdate, PatientResponse
from app.core.security import (
    get_current_user,
    get_current_patient,
    get_current_doctor,
    get_current_admin
)
from app.services.patient_service import (
    get_patient_by_user_id,
    get_patient_by_id,
    get_all_patients,
    update_patient_profile,
    search_patients
)

router = APIRouter()


# ── GET /api/patients/me ────────────────────────────────────
@router.get("/me", response_model=PatientResponse)
def get_my_profile(
    current_user: User    = Depends(get_current_patient),
    db:           Session = Depends(get_db)
):
    """
    Patient apna profile dekhe
    Sirf patient access kar sakta hai
    """
    return get_patient_by_user_id(current_user.id, db)


# ── PUT /api/patients/me ────────────────────────────────────
@router.put("/me", response_model=PatientResponse)
def update_my_profile(
    payload:      PatientUpdate,
    current_user: User    = Depends(get_current_patient),
    db:           Session = Depends(get_db)
):
    """Patient apna profile update kare"""
    patient = get_patient_by_user_id(current_user.id, db)
    return update_patient_profile(patient.id, payload, db)


# ── GET /api/patients/ ──────────────────────────────────────
@router.get("/")
def list_patients(
    skip:         int            = Query(0, ge=0),
    limit:        int            = Query(50, le=100),
    current_user: User           = Depends(get_current_doctor),
    db:           Session        = Depends(get_db)
):
    """
    Sab patients ki list
    Sirf Doctor ya Admin dekh sakta hai
    """
    return get_all_patients(db, skip=skip, limit=limit)


# ── GET /api/patients/search ────────────────────────────────
@router.get("/search")
def search(
    q:            str     = Query(..., min_length=2, description="Name, phone, ya email"),
    current_user: User    = Depends(get_current_doctor),
    db:           Session = Depends(get_db)
):
    """
    Patient search karo
    Doctor consultation ke waqt patient dhundne ke liye
    """
    return search_patients(q, db)


# ── GET /api/patients/{patient_id} ─────────────────────────
@router.get("/{patient_id}", response_model=PatientResponse)
def get_patient(
    patient_id:   UUID,
    current_user: User    = Depends(get_current_user),
    db:           Session = Depends(get_db)
):
    """
    Specific patient ki detail
    Doctor → koi bhi patient dekh sakta hai
    Patient → sirf apna profile dekh sakta hai
    """
    patient = get_patient_by_id(patient_id, db)

    # Patient sirf apna profile dekh sakta hai
    if current_user.role == "patient":
        own = get_patient_by_user_id(current_user.id, db)
        if own.id != patient_id:
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="Access denied")

    return patient


# ── PUT /api/patients/{patient_id} ─────────────────────────
@router.put("/{patient_id}", response_model=PatientResponse)
def update_patient(
    patient_id:   UUID,
    payload:      PatientUpdate,
    current_user: User    = Depends(get_current_admin),
    db:           Session = Depends(get_db)
):
    """
    Admin kisi bhi patient ka profile update kare
    """
    return update_patient_profile(patient_id, payload, db)