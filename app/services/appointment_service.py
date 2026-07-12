from sqlalchemy.orm import Session
from fastapi import HTTPException
from uuid import UUID
from datetime import date, datetime, timedelta

from app.models.appointment import Appointment, AppointmentStatus
from app.models.patient import Patient
from app.models.doctor import Doctor
from app.models.reminder import Reminder, ReminderType, ReminderChannel
from app.schemas.appointment import AppointmentCreate, AppointmentUpdate


# ── Helper: Patient nikalo ──────────────────────────────────
def get_patient_by_user(user_id: UUID, db: Session) -> Patient:
    patient = db.query(Patient).filter(Patient.user_id == user_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient profile not found")
    return patient


# ── Helper: Doctor active hai? ──────────────────────────────
def get_active_doctor(doctor_id: UUID, db: Session) -> Doctor:
    doctor = db.query(Doctor).filter(
        Doctor.id == doctor_id,
        Doctor.is_active == True
    ).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found or inactive")
    return doctor


# ── Helper: Slot available hai? ────────────────────────────
def check_slot_available(
    doctor_id:        UUID,
    appointment_date: date,
    slot_time:        str,
    db:               Session,
    exclude_id:       UUID = None   # reschedule ke liye
) -> None:
    """
    Double booking check karo
    Agar slot already booked hai → 409 error
    """
    query = db.query(Appointment).filter(
        Appointment.doctor_id        == doctor_id,
        Appointment.appointment_date == appointment_date,
        Appointment.slot_time        == slot_time,
        Appointment.status.in_([
            AppointmentStatus.pending,
            AppointmentStatus.confirmed
        ])
    )

    # Reschedule case mein apna hi appointment exclude karo
    if exclude_id:
        query = query.filter(Appointment.id != exclude_id)

    existing = query.first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Slot {slot_time} on {appointment_date} is already booked"
        )


# ── Helper: Date valid hai? ─────────────────────────────────
def validate_appointment_date(appointment_date: date) -> None:
    """Past date pe booking nahi ho sakti"""
    if appointment_date < date.today():
        raise HTTPException(
            status_code=400,
            detail="Cannot book appointment in the past"
        )


# ── Helper: Doctor available hai is din? ───────────────────
def validate_doctor_availability(doctor: Doctor, appointment_date: date) -> None:
    """Doctor us din available hai?"""
    day_name = appointment_date.strftime("%a")  # Mon, Tue...
    if doctor.available_days and day_name not in doctor.available_days:
        raise HTTPException(
            status_code=400,
            detail=f"Doctor is not available on {day_name}"
        )


# ── Helper: Reminders schedule karo ────────────────────────
def schedule_reminders(appointment: Appointment, db: Session) -> None:
    """
    Appointment book hone ke baad
    24h aur 2h ke reminders schedule karo
    """
    appt_datetime = datetime.combine(
        appointment.appointment_date,
        appointment.slot_time
    )

    reminders_to_create = [
        # 24 ghante pehle
        Reminder(
            appointment_id=appointment.id,
            type="24h",
            channel=ReminderChannel.whatsapp,
            scheduled_at=appt_datetime - timedelta(hours=24)
        ),
        # 2 ghante pehle
        Reminder(
            appointment_id=appointment.id,
            type="2h",
            channel=ReminderChannel.whatsapp,
            scheduled_at=appt_datetime - timedelta(hours=2)
        ),
    ]

    for reminder in reminders_to_create:
        # Sirf future reminders add karo
        if reminder.scheduled_at > datetime.utcnow():
            db.add(reminder)


# ════════════════════════════════════════════════════════════
# MAIN SERVICE FUNCTIONS
# ════════════════════════════════════════════════════════════

def book_appointment(
    payload:  AppointmentCreate,
    user_id:  UUID,
    db:       Session
) -> Appointment:
    """
    Appointment book karo
    
    Steps:
    1. Patient nikalo
    2. Doctor check karo
    3. Date validate karo
    4. Doctor availability check karo
    5. Slot available hai?
    6. Appointment save karo
    7. Reminders schedule karo
    """

    # 1. Patient nikalo
    patient = get_patient_by_user(user_id, db)

    # 2. Doctor check karo
    doctor = get_active_doctor(payload.doctor_id, db)

    # 3. Date past mein nahi honi chahiye
    validate_appointment_date(payload.appointment_date)

    # 4. Doctor us din available hai?
    validate_doctor_availability(doctor, payload.appointment_date)

    # 5. Slot already booked nahi hona chahiye
    check_slot_available(
        payload.doctor_id,
        payload.appointment_date,
        payload.slot_time,
        db
    )

    # 6. Appointment banao
    appointment = Appointment(
        patient_id=patient.id,
        doctor_id=payload.doctor_id,
        appointment_date=payload.appointment_date,
        slot_time=payload.slot_time,
        reason=payload.reason,
        booked_via=payload.booked_via,
        status=AppointmentStatus.pending
    )
    db.add(appointment)
    db.flush()  # ID generate karo

    # 7. Reminders schedule karo
    schedule_reminders(appointment, db)

    db.commit()
    db.refresh(appointment)
    return appointment


def get_patient_appointments(
    user_id: UUID,
    status:  str,
    db:      Session
):
    """Patient ki appointments lo"""
    patient = get_patient_by_user(user_id, db)

    query = db.query(Appointment).filter(
        Appointment.patient_id == patient.id
    )

    if status:
        query = query.filter(Appointment.status == status)

    return query.order_by(
        Appointment.appointment_date.desc(),
        Appointment.slot_time.desc()
    ).all()


def get_doctor_appointments(
    user_id:          UUID,
    appointment_date: date,
    status:           str,
    db:               Session
):
    """Doctor ki appointments lo — apna schedule dekhe"""
    doctor = db.query(Doctor).filter(Doctor.user_id == user_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    query = db.query(Appointment).filter(
        Appointment.doctor_id == doctor.id
    )

    if appointment_date:
        query = query.filter(Appointment.appointment_date == appointment_date)

    if status:
        query = query.filter(Appointment.status == status)

    return query.order_by(
        Appointment.appointment_date.asc(),
        Appointment.slot_time.asc()
    ).all()


def get_appointment_by_id(appointment_id: UUID, db: Session) -> Appointment:
    """Single appointment nikalo"""
    appointment = db.query(Appointment).filter(
        Appointment.id == appointment_id
    ).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return appointment


def update_appointment_status(
    appointment_id: UUID,
    payload:        AppointmentUpdate,
    user_id:        UUID,
    role:           str,
    db:             Session
) -> Appointment:
    """
    Appointment status update karo
    
    Rules:
    - Patient: sirf cancel kar sakta hai (pending/confirmed)
    - Doctor: confirm, complete, no_show kar sakta hai
    - Admin: kuch bhi kar sakta hai
    """
    appointment = get_appointment_by_id(appointment_id, db)

    # Patient sirf apni appointment cancel kar sakta hai
    if role == "patient":
        patient = get_patient_by_user(user_id, db)
        if appointment.patient_id != patient.id:
            raise HTTPException(status_code=403, detail="Access denied")
        if payload.status != AppointmentStatus.cancelled:
            raise HTTPException(
                status_code=403,
                detail="Patients can only cancel appointments"
            )
        if appointment.status not in [
            AppointmentStatus.pending,
            AppointmentStatus.confirmed
        ]:
            raise HTTPException(
                status_code=400,
                detail="Cannot cancel — appointment is already completed or cancelled"
            )

    # Doctor sirf apni appointments update kar sakta hai
    elif role == "doctor":
        doctor = db.query(Doctor).filter(Doctor.user_id == user_id).first()
        if appointment.doctor_id != doctor.id:
            raise HTTPException(status_code=403, detail="Access denied")

    # Status update karo
    appointment.status = payload.status
    if payload.notes:
        appointment.notes = payload.notes

    db.commit()
    db.refresh(appointment)
    return appointment


def reschedule_appointment(
    appointment_id:   UUID,
    new_date:         date,
    new_slot:         str,
    user_id:          UUID,
    db:               Session
) -> Appointment:
    """
    Appointment reschedule karo
    Naya slot available hona chahiye
    """
    appointment = get_appointment_by_id(appointment_id, db)

    # Sirf patient apni appointment reschedule kar sakta hai
    patient = get_patient_by_user(user_id, db)
    if appointment.patient_id != patient.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Cancelled/completed appointment reschedule nahi ho sakti
    if appointment.status in [
        AppointmentStatus.cancelled,
        AppointmentStatus.completed
    ]:
        raise HTTPException(
            status_code=400,
            detail="Cannot reschedule cancelled or completed appointment"
        )

    # Naya date validate karo
    validate_appointment_date(new_date)

    # Naya slot available hai?
    check_slot_available(
        appointment.doctor_id,
        new_date,
        new_slot,
        db,
        exclude_id=appointment_id  # apna slot exclude karo
    )

    # Update karo
    appointment.appointment_date = new_date
    appointment.slot_time        = new_slot
    appointment.status           = AppointmentStatus.pending

    # Purane reminders delete karo
    from app.models.reminder import ReminderStatus
    db.query(Reminder).filter(
        Reminder.appointment_id == appointment_id,
        Reminder.status         == ReminderStatus.pending
    ).delete()

    # Naye reminders banao
    schedule_reminders(appointment, db)

    db.commit()
    db.refresh(appointment)
    return appointment


def get_all_appointments(
    db:               Session,
    appointment_date: date = None,
    status:           str  = None,
    doctor_id:        UUID = None,
    skip:             int  = 0,
    limit:            int  = 50
):
    """Admin ke liye — sab appointments"""
    query = db.query(Appointment)

    if appointment_date:
        query = query.filter(Appointment.appointment_date == appointment_date)
    if status:
        query = query.filter(Appointment.status == status)
    if doctor_id:
        query = query.filter(Appointment.doctor_id == doctor_id)

    return query.order_by(
        Appointment.appointment_date.desc(),
        Appointment.slot_time.desc()
    ).offset(skip).limit(limit).all()