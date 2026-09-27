import re
import secrets
import logging

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.clinic import Clinic
from app.models.clinincAdmin import ClinicAdmin
from app.models.user import User
from app.core.security import hash_password, settings
from app.schemas.clinic import CreateClinicRequest, ClinicResponse
from app.services.email_Service import send_clinic_admin_welcome_email
from datetime import date

from sqlalchemy.orm import Session
from fastapi import HTTPException


from app.models.doctor import Doctor
from app.models.appointment import Appointment
from app.models.patient import Patient
logger = logging.getLogger(__name__)


# ── Helper: unique slug banao clinic ke naam se ─────────────────────────────
def generate_slug(name: str, db: Session) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    slug, i = base, 1
    while db.query(Clinic).filter(Clinic.slug == slug).first():  # ← fixed: slug, not clinic_name
        slug = f"{base}-{i}"
        i += 1
    return slug


# ════════════════════════════════════════════════════════════
# MAIN SERVICE FUNCTION
# ════════════════════════════════════════════════════════════
def create_clinic(payload: CreateClinicRequest, db: Session) -> ClinicResponse:
    """
    Creates a new clinic AND its first Clinic Admin account in one step.

    Steps:
    1. Check admin email isn't already in use
    2. Generate a unique slug for the clinic
    3. Create the Clinic row (including payment settings)
    4. Create the Clinic Admin's User row (temp password)
    5. Link them via ClinicAdmin
    6. Commit
    7. Send welcome email (non-blocking — failure here must not fail the request)
    """

    # 1. Admin email already used?
    if db.query(User).filter(User.email == payload.admin_email).first():
        raise HTTPException(status_code=400, detail="Admin email already in use")

    # 2. Generate slug
    slug = generate_slug(payload.clinic_name, db)

    # 3. Create clinic — now includes payment fields and clinic email/country
    clinic = Clinic(
        clinic_name=payload.clinic_name,
        city=payload.city,
        country=payload.country,          # matches the (misspelled) column on your model
        email=payload.email,
        phone=payload.whatsapp_number,
        address=payload.address,
        slug=slug,
        clinic_status=True,

        payment_enabled=payload.payment_enabled,
        payment_provider=payload.payment_provider if payload.payment_enabled else None,
        stripe_payment_id=None,            # filled in later via Stripe Connect onboarding
    )
    db.add(clinic)
    db.flush()  # so clinic.clinic_id is available below

    # 4. Create the clinic admin's user account
    temp_password = secrets.token_urlsafe(8)
    admin_user = User(
        email=payload.admin_email,
        full_name=payload.admin_name,
        password=hash_password(temp_password),
        role="admin",               # ← fixed: was "admin", must match your role convention
        auth_provider="email",
    )
    db.add(admin_user)
    db.flush()

    # 5. Link user <-> clinic
    clinic_admin = ClinicAdmin(user_id=admin_user.id, clinic_id=clinic.clinic_id)
    db.add(clinic_admin)

    # 6. Commit — clinic + admin now exist regardless of what happens with email
    db.commit()
    db.refresh(clinic)

    # 7. Send welcome email — failure here should NOT fail the whole request,
    #    since the clinic and admin account already exist at this point.
    try:
        send_clinic_admin_welcome_email(
            admin_email=payload.admin_email,
            admin_name=payload.admin_name,
            clinic_name=clinic.clinic_name,
            temp_password=temp_password,
        )
    except Exception as e:
        logger.error(f"Failed to send welcome email to {payload.admin_email}: {e}")
        # Intentionally not re-raised — the clinic is created either way.
        # Consider adding a "resend welcome email" action in the Super Admin panel
        # for cases where this fails.

    return ClinicResponse(
        id=clinic.clinic_id,
        name=clinic.clinic_name,
        slug=slug,
        adminEmail=payload.admin_email,
        # NOTE: confirm which of these two this URL should actually be —
        # a patient-facing booking link, or the clinic admin's login link.
        # Renamed the field below to make the intent explicit; update your
        # ClinicResponse schema and frontend accordingly if you go this route.
        bookingUrl=f"{settings.FRONTEND_URL}/{slug}/signup",
    )
# Step 2-3: Clinic Admin "Connect Stripe" click kare
# @router.post("/admin/stripe/connect")
# def start_stripe_onboarding(clinic_admin = Depends(require_clinic_admin), db: Session = Depends(get_db)):
#     clinic = db.query(Clinic).filter(Clinic.clinic_id == clinic_admin.clinic_id).first()

#     # Stripe pe ek naya Connect account banao
#     account = stripe.Account.create(type="express", email=clinic.email)

#     # ID abhi save kar lo (account abhi verify nahi hua, lekin ID mil gayi)
#     clinic.stripe_payment_id = account.id   # ← "acct_1A2B3C..."
#     db.commit()

#     # Onboarding link banao aur user ko wahan bhej do
#     link = stripe.AccountLink.create(
#         account=account.id,
#         refresh_url=f"{FRONTEND_URL}/admin/settings",
#         return_url=f"{FRONTEND_URL}/admin/settings?stripe=connected",
#         type="account_onboarding",
#     )
#     return {"onboarding_url": link.url}




def admin_dashboard(
    db: Session,
    current_user: User,
):
    # ---------------------------------------------------------
    # 1. Find ClinicAdmin using logged-in user's ID
    # ---------------------------------------------------------

    clinic_admin = (
        db.query(ClinicAdmin)
        .filter(ClinicAdmin.user_id == current_user.id)
        .first()
    )

    if not clinic_admin:
        raise HTTPException(
            status_code=404,
            detail="Clinic admin record not found"
        )

    # ---------------------------------------------------------
    # 2. Get clinic
    # ---------------------------------------------------------

    clinic = clinic_admin.clinic

    if not clinic:
        raise HTTPException(
            status_code=404,
            detail="Clinic not found"
        )

    clinic_id = clinic.clinic_id

    # ---------------------------------------------------------
    # 3. Get doctors of this clinic
    # ---------------------------------------------------------

    doctors = (
        db.query(Doctor)
        .filter(Doctor.clinic_id == clinic_id)
        .all()
    )

    doctor_count = len(doctors)

    # ---------------------------------------------------------
    # 4. Get patients of this clinic
    # ---------------------------------------------------------

    patients = (
        db.query(Patient)
        .filter(Patient.clinic_id == clinic_id)
        .all()
    )

    patient_count = len(patients)

    # ---------------------------------------------------------
    # 5. Today's appointments
    # ---------------------------------------------------------

    today = date.today()

    appointments = (
        db.query(Appointment)
        .join(Doctor, Appointment.doctor_id == Doctor.id)
        .filter(
            Doctor.clinic_id == clinic_id,
            # Appointment date condition goes here
        )
        .all()
    )

    # ---------------------------------------------------------
    # 6. Return dashboard
    # ---------------------------------------------------------

    return {
        "clinic": {
            "id": clinic.clinic_id,
            "name": clinic.clinic_name,
            "email": clinic.email,
            "phone": clinic.phone,
            "address": clinic.address,
            "city": clinic.city,
            "logo": clinic.logo,
            "slug": clinic.slug,
        },

        "stats": {
            "doctors": doctor_count,
            "patients": patient_count,
            "today_appointments": len(appointments),
        },

        "doctors": [
            {
                "id": doctor.id,
                "user_id": doctor.user_id,
                "specialization": doctor.specialization,
                "qualification": doctor.qualification,
                "fee": doctor.fee,
                "is_active": doctor.is_active,
            }
            for doctor in doctors
        ],

        "appointments": appointments,
    }