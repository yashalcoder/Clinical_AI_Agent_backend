import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.doctor import Doctor
from app.models.clinincAdmin import ClinicAdmin
from app.models.doctor_invite import DoctorInvite, DoctorInviteStatus
from app.core.security import hash_password, create_access_token, get_current_user
from app.schemas.doctor_invite import (
    CreateDoctorInviteRequest,
    DoctorInviteResponse,
    InvitePreviewResponse,
    AcceptInviteRequest,
)
from app.services.email_Service import send_doctor_invite_email
from app.core.config import settings
router = APIRouter()

INVITE_EXPIRY_DAYS = 7


# ── Helper: sirf clinic_admin allowed, aur unka clinic_id nikal do ──────────
def require_clinic_admin(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ClinicAdmin:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")

    clinic_admin = db.query(ClinicAdmin).filter(ClinicAdmin.user_id == current_user.id).first()
    if not clinic_admin:
        raise HTTPException(status_code=404, detail="Clinic admin profile not found")

    return clinic_admin


# ════════════════════════════════════════════════════════════
# 1. Clinic Admin creates an invite
# ════════════════════════════════════════════════════════════
# POST /api/admin/doctors/invite
@router.post("/doctors/invite", response_model=DoctorInviteResponse, status_code=201)
def create_doctor_invite(
    payload: CreateDoctorInviteRequest,
    clinic_admin: ClinicAdmin = Depends(require_clinic_admin),
    db: Session = Depends(get_db),
):
    """Clinic admin invites a new doctor to their clinic — no self-signup for doctors."""

    email = payload.email.strip().lower()

    # Already a user with this email?
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="This email is already registered")

    # Already an unexpired pending invite for this email + clinic?
    existing = db.query(DoctorInvite).filter(
        DoctorInvite.email == email,
        DoctorInvite.clinic_id == clinic_admin.clinic_id,
        DoctorInvite.status == DoctorInviteStatus.pending,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="An invite is already pending for this email")

    invite = DoctorInvite(
        clinic_id=clinic_admin.clinic_id,
        email=email,
        specialization=payload.specialization,
        token=secrets.token_urlsafe(32),
        status=DoctorInviteStatus.pending,
        expires_at=datetime.now(timezone.utc) + timedelta(days=INVITE_EXPIRY_DAYS),
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)

    send_doctor_invite_email(
        email=invite.email,
        token=invite.token,
        clinic_name=clinic_admin.clinic.clinic_name,
    )

    return DoctorInviteResponse(
        id=invite.id,
        email=invite.email,
        specialization=invite.specialization,
        status=invite.status,
        expires_at=invite.expires_at,
        invite_url=f"{settings.FRONTEND_URL}/invite/{invite.token}",
    )
# ════════════════════════════════════════════════════════════
# 2. Public — doctor opens the invite link, frontend pre-fills the form
# ════════════════════════════════════════════════════════════
# GET /api/invite/{token}
@router.get("/invite/{token}", response_model=InvitePreviewResponse)
def preview_invite(token: str, db: Session = Depends(get_db)):
    invite = _get_valid_invite_or_404(token, db)

    return InvitePreviewResponse(
        email=invite.email,
        specialization=invite.specialization,
        clinic_name=invite.clinic.clinic_name,
    )

# ════════════════════════════════════════════════════════════
# Public — doctor completes the invite
# POST /api/invite/{token}/accept
# ════════════════════════════════════════════════════════════

@router.post("/invite/{token}/accept")
def accept_invite(
    token: str,
    payload: AcceptInviteRequest,
    db: Session = Depends(get_db),
):
    # Validate invite
    invite = _get_valid_invite_or_404(token, db)

    # Password validation
    if len(payload.password) < 8:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 8 characters",
        )

    # Validate name
    full_name = payload.full_name.strip()

    if not full_name:
        raise HTTPException(
            status_code=400,
            detail="Full name is required",
        )

    # Validate time
    if payload.start_time >= payload.end_time:
        raise HTTPException(
            status_code=400,
            detail="End time must be later than start time",
        )

    # Validate available days
    allowed_days = {
        "Mon",
        "Tue",
        "Wed",
        "Thu",
        "Fri",
        "Sat",
        "Sun",
    }

    invalid_days = set(payload.available_days) - allowed_days

    if invalid_days:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid available days: {', '.join(invalid_days)}",
        )

    if not payload.available_days:
        raise HTTPException(
            status_code=400,
            detail="Please select at least one available day",
        )

    # Make sure email hasn't already been registered
    existing_user = (
        db.query(User)
        .filter(User.email == invite.email)
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="This email is already registered",
        )

    try:
        # ════════════════════════════════════════════════════
        # 1. Create User
        # ════════════════════════════════════════════════════

        user = User(
            email=invite.email,
            full_name=full_name,
            password=hash_password(payload.password),
            role="doctor",
            auth_provider="email",
            is_active=True,
        )

        db.add(user)
        db.flush()

        # ════════════════════════════════════════════════════
        # 2. Create Doctor profile
        # ════════════════════════════════════════════════════

        doctor = Doctor(
            user_id=user.id,

            # IMPORTANT:
            # Clinic comes from invite, NOT from frontend
            clinic_id=invite.clinic_id,

            # Specialization also comes from invite
            specialization=invite.specialization or "General",

            # Profile fields from doctor
            qualification=payload.qualification.strip(),
            fee=payload.fee,
            available_days=payload.available_days,
            slot_duration=payload.slot_duration,
            start_time=payload.start_time,
            end_time=payload.end_time,

            # Backend controls this
            is_active=True,
        )

        db.add(doctor)

        # ════════════════════════════════════════════════════
        # 3. Mark invite as accepted
        # ════════════════════════════════════════════════════

        invite.status = DoctorInviteStatus.accepted

        db.commit()

        db.refresh(user)
        db.refresh(doctor)

    except Exception:
        db.rollback()
        raise

    # ════════════════════════════════════════════════════════
    # 4. Create JWT
    # ════════════════════════════════════════════════════════

    jwt_token = create_access_token(
        data={
            "sub": str(user.id),
            "role": user.role,
            "email": user.email,
            "clinic_id":invite.clinic_id,
        }
    )

    # ════════════════════════════════════════════════════════
    # 5. Return only serializable data
    # ════════════════════════════════════════════════════════

    return {
        "access_token": jwt_token,
        "role": user.role,
        "user_id": str(user.id),
        "doctor_id": str(doctor.id),
        "full_name": user.full_name,
        "email": user.email,
        "clinic_id": str(invite.clinic_id),
        "specialization": doctor.specialization,
        "qualification": doctor.qualification,
        "fee": doctor.fee,
        "available_days": doctor.available_days,
        "slot_duration": doctor.slot_duration,
        "start_time": doctor.start_time,
        "end_time": doctor.end_time,
    }

# ── Shared helper: fetch + validate an invite by token ──────────────────────
def _get_valid_invite_or_404(token: str, db: Session) -> DoctorInvite:
    invite = db.query(DoctorInvite).filter(DoctorInvite.token == token).first()

    if not invite:
        raise HTTPException(status_code=404, detail="Invite not found")

    if invite.status != DoctorInviteStatus.pending:
        raise HTTPException(status_code=400, detail="This invite is no longer valid")

    if invite.expires_at < datetime.now(timezone.utc):
        invite.status = DoctorInviteStatus.expired
        db.commit()
        raise HTTPException(status_code=400, detail="This invite has expired")

    return invite