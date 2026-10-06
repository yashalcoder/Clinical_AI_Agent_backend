from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from app.models.patient import Patient
from app.models.doctor import Doctor
from app.models.clinic import Clinic
from app.models.appointment import Appointment, AppointmentStatus, BookingChannel

from app.schemas.appointment import AppointmentCreate

from app.services.appointment_service import (
    get_active_doctor,
    validate_appointment_date,
    validate_doctor_availability,
    validate_slot_time,
    check_slot_available,
    check_patient_not_double_booked,
    check_daily_booking_limit,
    schedule_reminders,
)

import logging

logger = logging.getLogger(__name__)


def public_book_appointment_service(
    payload: AppointmentCreate,
    clinic_id: int,
    db: Session,
) -> Appointment:

    # ==========================================================
    # 1. Clinic check
    # ==========================================================

    clinic = (
        db.query(Clinic)
        .filter(
            Clinic.clinic_id == clinic_id,
            Clinic.clinic_status == True,
        )
        .first()
    )

    if not clinic:
        raise HTTPException(
            status_code=404,
            detail="Clinic not found or inactive",
        )

    # ==========================================================
    # 2. Doctor check
    # ==========================================================

    doctor = (
        db.query(Doctor)
        .filter(
            Doctor.id == payload.doctor_id,
            Doctor.clinic_id == clinic_id,
            Doctor.is_active == True,
        )
        .first()
    )

    if not doctor:
        raise HTTPException(
            status_code=404,
            detail="Doctor not found or does not belong to this clinic",
        )

    # ==========================================================
    # 3. Date past mein nahi honi chahiye
    # ==========================================================

    validate_appointment_date(
        payload.appointment_date
    )

    # ==========================================================
    # 4. Doctor us din available hai?
    # ==========================================================

    validate_doctor_availability(
        doctor,
        payload.appointment_date
    )

    # ==========================================================
    # 5. Slot valid + available hai
    # ==========================================================

    validate_slot_time(
        doctor,
        payload.appointment_date,
        payload.slot_time,
        db,
    )

    # ==========================================================
    # 6. Extra slot availability check
    # ==========================================================

    check_slot_available(
        payload.doctor_id,
        payload.appointment_date,
        payload.slot_time,
        db,
    )

    # ==========================================================
    # 7. Find existing User by email
    # ==========================================================

    user = (
        db.query(User)
        .filter(
            User.email == payload.email.lower().strip()
        )
        .first()
    )

    # ==========================================================
    # 8. User doesn't exist -> create User
    # ==========================================================

    if not user:

        user = User(
            email=payload.email.lower().strip(),
            full_name=payload.full_name.strip(),
            phone=payload.contact_no or payload.whatsapp_no,
            role=UserRole.patient,
            password=None,
            google_id=None,
            picture=None,
            auth_provider="email",
            is_active=True,
        )

        db.add(user)
        db.flush()

    # ==========================================================
    # 9. Find Patient for THIS clinic
    # ==========================================================

    patient = (
        db.query(Patient)
        .filter(
            Patient.user_id == user.id,
            Patient.clinic_id == clinic_id,
        )
        .first()
    )

    # ==========================================================
    # 10. Patient doesn't exist -> create Patient
    # ==========================================================

    if not patient:

        patient = Patient(
            user_id=user.id,
            clinic_id=clinic_id,
            whatsapp_no=payload.whatsapp_no,
        )

        db.add(patient)
        db.flush()

    # ==========================================================
    # 11. Patient double booking check
    # ==========================================================

    check_patient_not_double_booked(
        patient.id,
        payload.appointment_date,
        payload.slot_time,
        db,
    )

    # ==========================================================
    # 12. Daily booking limit
    # ==========================================================

    check_daily_booking_limit(
        patient.id,
        db,
    )

    # ==========================================================
    # 13. Create appointment
    # ==========================================================

    appointment = Appointment(
        patient_id=patient.id,
        doctor_id=doctor.id,
        appointment_date=payload.appointment_date,
        slot_time=payload.slot_time,
        reason=payload.reason,
        booked_via=BookingChannel.web,
        status=AppointmentStatus.confirmed,
    )

    db.add(appointment)

    # ==========================================================
    # 14. Flush
    # ==========================================================

    try:

        db.flush()

    except IntegrityError:

        db.rollback()

        raise HTTPException(
            status_code=409,
            detail=(
                "This slot was just booked by someone else. "
                "Please choose another slot."
            ),
        )

    # ==========================================================
    # 15. Schedule reminders
    # ==========================================================

    try:

        schedule_reminders(
            appointment,
            db,
        )

    except Exception as e:

        logger.error(
            f"Reminder scheduling failed for "
            f"appointment {appointment.id}: {e}"
        )

    # ==========================================================
    # 16. NO NOTIFICATIONS
    # ==========================================================
    #
    # Public booking mein notify() nahi karna.
    #
    # notify(
    #     user_id=doctor.user_id,
    #     ...
    # )
    #
    # notify(
    #     user_id=user.id,
    #     ...
    # )
    #
    # ==========================================================

    # ==========================================================
    # 17. Commit
    # ==========================================================

    db.commit()

    db.refresh(appointment)

    logger.info(
        f"Public appointment booked: "
        f"patient={patient.id}, "
        f"doctor={doctor.id}, "
        f"clinic={clinic_id}, "
        f"date={payload.appointment_date}, "
        f"slot={payload.slot_time}"
    )

    return appointment