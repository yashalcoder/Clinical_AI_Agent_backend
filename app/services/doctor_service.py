from sqlalchemy.orm import Session
from fastapi import HTTPException
from uuid import UUID
from datetime import date, time, timedelta, datetime
from typing import List

from app.models.doctor import Doctor
from app.models.user import User
from app.models.appointment import Appointment, AppointmentStatus
from app.schemas.doctor import DoctorCreate, DoctorUpdate


def get_doctor_by_user_id(user_id: UUID, db: Session) -> Doctor:
    """User ID se doctor nikalo"""
    doctor = db.query(Doctor).filter(Doctor.user_id == user_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor profile not found")
    return doctor


def get_doctor_by_id(doctor_id: UUID, db: Session) -> Doctor:
    """Doctor ID se doctor nikalo"""
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return doctor


def get_all_doctors(db: Session, specialization: str = None):
    """
    Sab active doctors lo
    Patient appointment book karne ke liye use kare
    """
    query = (
        db.query(Doctor, User)
        .join(User, Doctor.user_id == User.id)
        .filter(Doctor.is_active == True, User.is_active == True)
    )

    if specialization:
        query = query.filter(
            Doctor.specialization.ilike(f"%{specialization}%")
        )

    doctors = query.all()

    result = []
    for doctor, user in doctors:
        result.append({
            "id":             doctor.id,
            "user_id":        doctor.user_id,
            "full_name":      user.full_name,
            "email":          user.email,
            "phone":          user.phone,
            "picture":        user.picture,
            "specialization": doctor.specialization,
            "qualification":  doctor.qualification,
            "fee":            float(doctor.fee) if doctor.fee else 0,
            "available_days": doctor.available_days,
            "slot_duration":  doctor.slot_duration,
            "start_time":     str(doctor.start_time),
            "end_time":       str(doctor.end_time),
        })
    return result


def get_available_slots(
    doctor_id: UUID,
    date_req:  date,
    db:        Session
) -> List[str]:
    """
    Kisi bhi doctor ke liye specific date pe available slots nikalo
    
    Logic:
    1. Doctor ka schedule dekho (start/end time, slot_duration)
    2. Us date pe jo appointments booked hain nikalo
    3. Booked slots minus karo → available slots return karo
    """
    doctor = get_doctor_by_id(doctor_id, db)

    # Day name check karo
    day_name = date_req.strftime("%a")  # Mon, Tue, Wed...
    if doctor.available_days and day_name not in doctor.available_days:
        return []   # Doctor available nahi is din

    # Sab possible slots banao
    all_slots = []
    current = datetime.combine(date_req, doctor.start_time)
    end     = datetime.combine(date_req, doctor.end_time)
    delta   = timedelta(minutes=doctor.slot_duration)

    while current < end:
        all_slots.append(current.strftime("%H:%M"))
        current += delta

    # Jo slots pehle se booked hain woh nikalo
    booked = db.query(Appointment.slot_time).filter(
        Appointment.doctor_id        == doctor_id,
        Appointment.appointment_date == date_req,
        Appointment.status.in_([
            AppointmentStatus.pending,
            AppointmentStatus.confirmed
        ])
    ).all()

    booked_times = {str(b.slot_time)[:5] for b in booked}  # "09:00" format

    # Available = All - Booked
    available = [s for s in all_slots if s not in booked_times]
    return available


def update_doctor_profile(
    doctor_id: UUID,
    payload:   DoctorUpdate,
    db:        Session
) -> Doctor:
    """Doctor profile update karo"""
    doctor = get_doctor_by_id(doctor_id, db)

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(doctor, field, value)

    db.commit()
    db.refresh(doctor)
    return doctor