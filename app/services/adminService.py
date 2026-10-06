from fastapi import HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from app.models.clinincAdmin import ClinicAdmin


def get_admin_clinic_id(user_id, db: Session) -> int:
    clinic_admin = (
        db.query(ClinicAdmin)
        .filter(ClinicAdmin.user_id == user_id)
        .first()
    )

    if not clinic_admin:
        raise HTTPException(
            status_code=404,
            detail="Clinic admin profile not found"
        )

    return clinic_admin.clinic_id