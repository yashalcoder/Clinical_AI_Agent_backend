from sqlalchemy.orm import Session
from fastapi import HTTPException
from uuid import UUID
from datetime import date, datetime, timedelta
from sqlalchemy.exc import IntegrityError
from app.models.appointment import Appointment, AppointmentStatus
from app.models.patient import Patient
from app.models.doctor import Doctor
from app.models.reminder import Reminder, ReminderType, ReminderChannel
from app.schemas.appointment import AppointmentCreate, AppointmentUpdate
from app.services.doctor_service import get_available_slots
import logging
logger = logging.getLogger(__name__)
# Valid status transitions — kaunsi state se kaunsi state mein ja sakte hain
VALID_TRANSITIONS = {
    AppointmentStatus.pending:   [AppointmentStatus.confirmed, AppointmentStatus.cancelled],
    AppointmentStatus.confirmed: [AppointmentStatus.completed, AppointmentStatus.cancelled, AppointmentStatus.no_show],
    AppointmentStatus.completed: [],   # terminal state — yahan se kahin nahi ja sakta
    AppointmentStatus.cancelled: [],   # terminal state
    AppointmentStatus.no_show:   [],   # terminal state
}

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

def check_patient_not_double_booked(patient_id, appointment_date, slot_time, db):
    existing = db.query(Appointment).filter(
        Appointment.patient_id == patient_id,
        Appointment.appointment_date == appointment_date,
        Appointment.slot_time == slot_time,
        Appointment.status.in_([AppointmentStatus.pending, AppointmentStatus.confirmed])
    ).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail="You already have an appointment at this time."
        )
# ── Helper: Reminders schedule karo ────────────────────────
def schedule_reminders(appointment: Appointment, db: Session) -> None:
    appt_datetime = datetime.combine(appointment.appointment_date, appointment.slot_time)

    reminders_to_create = [
        # Turant confirmation (booking ke turant baad bhejne ke liye)
        Reminder(
            appointment_id=appointment.id,
            type=ReminderType.confirm,
            channel=ReminderChannel.whatsapp,
            scheduled_at=datetime.utcnow()  # turant
        ),
        Reminder(
            appointment_id=appointment.id,
            type=ReminderType.h24,
            channel=ReminderChannel.whatsapp,
            scheduled_at=appt_datetime - timedelta(hours=24)
        ),
        Reminder(
            appointment_id=appointment.id,
            type=ReminderType.h2,
            channel=ReminderChannel.whatsapp,
            scheduled_at=appt_datetime - timedelta(hours=2)
        ),
    ]

    for reminder in reminders_to_create:
        if reminder.scheduled_at > datetime.utcnow() - timedelta(minutes=1):  # thoda buffer confirm ke liye
            db.add(reminder)
def check_daily_booking_limit(patient_id, db, max_per_day=10):
    today_start = datetime.combine(date.today(), datetime.min.time())
    today_count = db.query(Appointment).filter(
        Appointment.patient_id == patient_id,
        Appointment.created_at >= today_start
    ).count()
    if today_count >= max_per_day:
        raise HTTPException(status_code=429, detail="Daily booking limit reached")
def validate_slot_time(doctor: Doctor, appointment_date: date, slot_time, db: Session) -> None:
    """
    slot_time: datetime.time object (payload se aata hai)
    """
    available_slots = get_available_slots(doctor.id, appointment_date, db)  # list of "HH:MM" strings

    slot_time_str = slot_time.strftime("%H:%M")  # time object ko string mein convert karo comparison ke liye

    if slot_time_str not in available_slots:
        raise HTTPException(
            status_code=400,
            detail=f"Slot {slot_time_str} is not available. Please choose from available slots."
        )
# ════════════════════════════════════════════════════════════
# MAIN SERVICE FUNCTIONS
# ════════════════════════════════════════════════════════════
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

def book_appointment(payload: AppointmentCreate, user_id: UUID, db: Session) -> Appointment:
    # 1. Patient nikalo
    patient = get_patient_by_user(user_id, db)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient profile not found")

    # 2. Doctor check karo
    doctor = get_active_doctor(payload.doctor_id, db)

    # 3. Date past mein nahi honi chahiye
    validate_appointment_date(payload.appointment_date)

    # 4. Doctor us din available hai?
    validate_doctor_availability(doctor, payload.appointment_date)

  # Slot valid + available hai? (dono check ek function mein)
    validate_slot_time(doctor, payload.appointment_date, payload.slot_time, db)

    # Extra safety layer (redundant ho sakta hai, lekin theek hai rakhna)
    check_slot_available(payload.doctor_id, payload.appointment_date, payload.slot_time, db)

    # 7. Patient khud kisi aur doctor ke paas isi time pe booked to nahi?
    check_patient_not_double_booked(patient.id, payload.appointment_date, payload.slot_time, db)

    # 8. Daily limit check (abuse prevention)
    check_daily_booking_limit(patient.id, db)

    # 9. Appointment banao
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

    try:
        db.flush()  # DB unique constraint yahan race condition catch karega
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="This slot was just booked by someone else. Please choose another slot."
        )

    # 10. Reminders — fail ho to bhi booking continue rahe
    try:
        schedule_reminders(appointment, db)
    except Exception as e:
        logger.error(f"Reminder scheduling failed for appointment {appointment.id}: {e}")

    db.commit()
    db.refresh(appointment)

    logger.info(f"Appointment booked: patient={patient.id}, doctor={doctor.id}, date={payload.appointment_date}, slot={payload.slot_time}")

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
    - Sab roles ke liye: status transition valid honi chahiye
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
        if not doctor:
            raise HTTPException(status_code=404, detail="Doctor profile not found")
        if appointment.doctor_id != doctor.id:
            raise HTTPException(status_code=403, detail="Access denied")

    # Admin ke liye koi restriction nahi (role == "admin" case yahan gir jayega, aage badhega)

    # ── Status transition validation — SAB roles (patient/doctor/admin) ke liye common ──
    # Note: Admin ko bhi terminal states se transition allow nahi karna chahiye,
    # data-integrity ke liye — agar admin ko override chahiye ho kabhi, alag "force" flag rakh sakte hain
    allowed_next_states = VALID_TRANSITIONS.get(appointment.status, [])
    if payload.status not in allowed_next_states:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot change status from '{appointment.status.value}' to '{payload.status.value}'"
        )

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
    new_slot,   # time object
    user_id:          UUID,
    db:               Session
) -> Appointment:
    appointment = get_appointment_by_id(appointment_id, db)

    patient = get_patient_by_user(user_id, db)
    if appointment.patient_id != patient.id:
        raise HTTPException(status_code=403, detail="Access denied")

    if appointment.status in [AppointmentStatus.cancelled, AppointmentStatus.completed]:
        raise HTTPException(status_code=400, detail="Cannot reschedule cancelled or completed appointment")

    # Naya date validate karo
    validate_appointment_date(new_date)

    # ── Ye 2 lines add karo ──
    doctor = get_active_doctor(appointment.doctor_id, db)
    validate_doctor_availability(doctor, new_date)
    validate_slot_time(doctor, new_date, new_slot, db)
    # ─────────────────────────

    check_slot_available(appointment.doctor_id, new_date, new_slot, db, exclude_id=appointment_id)

    appointment.appointment_date = new_date
    appointment.slot_time        = new_slot
    appointment.status           = AppointmentStatus.pending

    from app.models.reminder import ReminderStatus
    db.query(Reminder).filter(
        Reminder.appointment_id == appointment_id,
        Reminder.status         == ReminderStatus.pending
    ).delete()

    schedule_reminders(appointment, db)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="This slot was just booked. Please choose another.")
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