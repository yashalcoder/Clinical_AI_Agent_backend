
# find clinic_id by slug
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.clinic import Clinic

router = APIRouter()


@router.get("/by-slug/{slug}")
def get_clinic_by_slug(
    slug: str,
    db: Session = Depends(get_db)
):
    clinic = (
        db.query(Clinic)
        .filter(
            Clinic.slug == slug,
            Clinic.clinic_status == True
        )
        .first()
    )

    if not clinic:
        raise HTTPException(
            status_code=404,
            detail="Clinic not found"
        )

    return {
        "clinic_id": clinic.clinic_id,
        "name": clinic.clinic_name,
        "slug": clinic.slug
    }