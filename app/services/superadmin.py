import re
import secrets

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.clinic import Clinic
from app.models.clinincAdmin import ClinicAdmin
from app.models.user import User
from app.core.security import hash_password,settings
from app.schemas.clinic import CreateClinicRequest, ClinicResponse
from app.services.email_Service import send_clinic_admin_welcome_email

# ── Helper: unique slug banao clinic ke naam se ─────────────────────────────
def generate_slug(name: str, db: Session) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    slug, i = base, 1
    while db.query(Clinic).filter(Clinic.clinic_name == slug).first():  # adjust field/column if you add a real slug column
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
    3. Create the Clinic row
    4. Create the Clinic Admin's User row (temp password)
    5. Link them via ClinicAdmin
    6. TODO: email the temp password to the new admin
    """

    # 1. Admin email already used?
    if db.query(User).filter(User.email == payload.admin_email).first():
        raise HTTPException(status_code=400, detail="Admin email already in use")

    # 2. Generate slug
    slug = generate_slug(payload.clinic_name, db)

    # 3. Create clinic
    clinic = Clinic(
        clinic_name=payload.clinic_name,
        city=payload.city,
        phone=payload.whatsapp_number,
        address=payload.address,
        slug=slug,
        # TODO: map payload.whatsapp_number to the correct column once added to the Clinic model
    )
    db.add(clinic)
    db.flush()  # so clinic.clinic_id is available below

    # 4. Create the clinic admin's user account
    temp_password = secrets.token_urlsafe(8)
    admin_user = User(
        email=payload.admin_email,
        full_name=payload.admin_name,
        password=hash_password(temp_password),
        role="admin",
        auth_provider="email",
    )
    db.add(admin_user)
    db.flush()

    # 5. Link user <-> clinic
    clinic_admin = ClinicAdmin(user_id=admin_user.id, clinic_id=clinic.clinic_id)
    db.add(clinic_admin)

    db.commit()
    db.refresh(clinic)

    # 6. TODO: send temp_password to payload.admin_email via your email service
    # 7. Send welcome email
  
    send_clinic_admin_welcome_email(
        admin_email=payload.admin_email,
        admin_name=payload.admin_name,
        clinic_name=clinic.clinic_name,
        temp_password=temp_password,
    )
    print(f"Email sent to {payload.admin_email}")
    return ClinicResponse(
        id=clinic.clinic_id,
        name=clinic.clinic_name,
        slug=slug,
        adminEmail=payload.admin_email,
        bookingUrl=f"{settings.FRONTEND_URL}/{slug}/login",
    )