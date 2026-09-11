from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.core.security import get_current_platform_admin
from app.schemas.clinic import CreateClinicRequest, ClinicResponse
from app.services.superadmin import create_clinic as create_clinic_service

router = APIRouter()


# ── POST /api/superadmin/clinics ────────────────────────────
@router.post("/clinics", response_model=ClinicResponse, status_code=201)
def create_clinic(
    payload: CreateClinicRequest,
    current_user: User = Depends(get_current_platform_admin),  # ← role check runs FIRST
    db: Session = Depends(get_db),
):
    """
    Create a new clinic + its first Clinic Admin.
    Only reachable by platform_admin — get_current_platform_admin
    raises 403 before this function body ever runs otherwise.
    """
    return create_clinic_service(payload, db)