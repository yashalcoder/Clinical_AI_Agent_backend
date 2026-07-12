from sqlalchemy.orm import Session
from fastapi import HTTPException
from uuid import UUID
from app.models.patient import Patient
from app.models.user import User
from app.schemas.patient import PatientCreate, PatientUpdate


def get_patient_by_user_id(user_id: UUID, db: Session) -> Patient:
    """User ID se patient nikalo"""
    patient = db.query(Patient).filter(Patient.user_id == user_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient profile not found")
    return patient


def get_patient_by_id(patient_id: UUID, db: Session) -> Patient:
    """Patient ID se patient nikalo"""
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


def get_all_patients(db: Session, skip: int = 0, limit: int = 50):
    """
    Sab patients lo — Admin/Doctor ke liye
    skip + limit = pagination
    """
    patients = (
        db.query(Patient, User)
        .join(User, Patient.user_id == User.id)
        .filter(User.is_active == True)
        .offset(skip)
        .limit(limit)
        .all()
    )

    result = []
    for patient, user in patients:
        result.append({
            "id":           patient.id,
            "user_id":      patient.user_id,
            "full_name":    user.full_name,
            "email":        user.email,
            "phone":        user.phone,
            "date_of_birth": patient.date_of_birth,
            "gender":       patient.gender,
            "blood_group":  patient.blood_group,
            "whatsapp_no":  patient.whatsapp_no,
            "address":      patient.address,
        })
    return result


def update_patient_profile(
    patient_id: UUID,
    payload: PatientUpdate,
    db: Session
) -> Patient:
    """Patient profile update karo"""
    patient = get_patient_by_id(patient_id, db)

    # Sirf jo fields aaye hain woh update karo
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(patient, field, value)

    db.commit()
    db.refresh(patient)
    return patient


def search_patients(query: str, db: Session):
    """Name ya phone se patient search karo — Doctor ke liye"""
    patients = (
        db.query(Patient, User)
        .join(User, Patient.user_id == User.id)
        .filter(
            User.is_active == True,
            (User.full_name.ilike(f"%{query}%")) |
            (User.phone.ilike(f"%{query}%")) |
            (User.email.ilike(f"%{query}%"))
        )
        .limit(20)
        .all()
    )

    result = []
    for patient, user in patients:
        result.append({
            "id":        patient.id,
            "full_name": user.full_name,
            "email":     user.email,
            "phone":     user.phone,
            "whatsapp_no": patient.whatsapp_no,
        })
    return result