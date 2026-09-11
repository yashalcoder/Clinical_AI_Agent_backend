import logging
import secrets
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.database import get_db
from app.models.clinic import Clinic
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.user import User, UserRole
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UpdateRoleRequest,
    UserResponse,
)
from app.services.google_oauth import (
    exchange_code_for_token,
    get_google_auth_url,
    get_google_user_info,
)

logger = logging.getLogger(__name__)
router = APIRouter()

VALID_ROLES = {"patient", "doctor", "clinic_admin"}


# ── Helper Functions ──────────────────────────────────────────

def resolve_clinic_by_slug(slug: Optional[str], role: str, db: Session) -> Optional[Clinic]:
    """
    Validates and fetches the clinic by slug for patient and doctor roles.
    Raises HTTPException if slug is missing or invalid.
    """
    if role in ("patient", "doctor"):
        if not slug:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Clinic slug is required for {role} registration."
            )
        
        clinic = db.query(Clinic).filter(Clinic.slug == slug).first()
        if not clinic:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Clinic not found for the provided slug."
            )
        return clinic
    return None

def get_clinic_id_for_user(user: User, db: Session) -> Optional[int]:
    """
    Fetch the clinic_id associated with the user based on their role profile.
    """
    if getattr(user, "role", None) == UserRole.patient:
        patient = db.query(Patient).filter(Patient.user_id == user.id).first()
        return patient.clinic_id if patient else None

    if getattr(user, "role", None) == UserRole.doctor:
        doctor = db.query(Doctor).filter(Doctor.user_id == user.id).first()
        return doctor.clinic_id if doctor else None

    return None

def generate_user_token(user: User, db: Session) -> str:
    """
    Generates a JWT access token containing sub, role, email, and clinic_id.
    """
    clinic_id = get_clinic_id_for_user(user, db)
    token_payload = {
        "sub": str(user.id),
        "role": user.role,
        "email": user.email,
        "clinic_id": clinic_id
    }
    return create_access_token(data=token_payload)

def create_role_profile(user: User, db: Session, clinic_id: Optional[int] = None):
    """
    Creates patient or doctor profile records mapped to a user and clinic.
    """
    if user.role == UserRole.patient:
        existing = db.query(Patient).filter(Patient.user_id == user.id).first()
        if not existing:
            db.add(Patient(user_id=user.id, clinic_id=clinic_id))

    elif user.role == UserRole.doctor:
        existing = db.query(Doctor).filter(Doctor.user_id == user.id).first()
        if not existing:
            db.add(Doctor(
                user_id=user.id,
                specialization="General",
                clinic_id=clinic_id
            ))

# ════════════════════════════════════
# EMAIL AUTH ROUTES
# ════════════════════════════════════

@router.post("/register", response_model=TokenResponse, status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user via Email"""

    email = payload.email.strip().lower()
    first_name = payload.firstName.strip()
    last_name = (payload.lastName or "").strip()
    role = (payload.role or "").strip().lower()
    phone = (payload.phone or "").strip()
    slug = getattr(payload, "slug", None)

    if not first_name:
        raise HTTPException(status_code=400, detail="First name is required")

    if role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail="Invalid account role")

    if len(payload.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    # 1. Resolve clinic via slug for patients/doctors
    clinic = resolve_clinic_by_slug(slug=slug, role=role, db=db)
    resolved_clinic_id = clinic.clinic_id if clinic else None

    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    if phone and db.query(User).filter(User.phone == phone).first():
        raise HTTPException(status_code=400, detail="Phone number already registered")

    full_name = f"{first_name} {last_name}".strip()

    # 2. Base User creation without clinic_id on User model (unless clinic_admin)
  # User Model mein clinic_id nahi bhejni
    user = User(
        email=email,
        full_name=full_name,
        phone=phone,
        role=role,
        password=hash_password(payload.password),
        auth_provider="email",
        is_active=True
    )

    try:
        db.add(user)
        db.flush()

        # 3. Attach clinic_id to Patient/Doctor profile table
        create_role_profile(user, db, clinic_id=resolved_clinic_id)

        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Email already registered")
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Could not create account, please try again")

    db.refresh(user)

    token = generate_user_token(user, db)
    return TokenResponse(
        access_token=token,
        role=user.role,
        user_id=user.id,
        full_name=user.full_name,
        is_new_user=True
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """Login via email and password"""

    user = db.query(User).filter(User.email == payload.email).first()

    if not user or not user.password:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not verify_password(payload.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if user.auth_provider == "google":
        raise HTTPException(
            status_code=400,
            detail="This account uses Google login. Please use 'Login with Google'."
        )

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account deactivated")

    token = generate_user_token(user, db)

    return TokenResponse(
        access_token=token,
        role=user.role,
        user_id=user.id,
        full_name=user.full_name,
        picture=user.picture
    )


# ════════════════════════════════════
# GOOGLE OAUTH ROUTES
# ════════════════════════════════════

@router.get("/google")
def google_login(
    role: str = Query("patient"),
    origin: str = Query("signup"),
    slug: Optional[str] = Query(None)
):
    if role not in ("patient", "doctor", "clinic_admin"):
        role = "patient"
    if origin not in ("signup", "login"):
        origin = "signup"

    raw_token = secrets.token_urlsafe(16)
    slug_str = slug if slug else ""
    state = f"{raw_token}:{role}:{origin}:{slug_str}"

    auth_url = get_google_auth_url(state=state)
    return RedirectResponse(url=auth_url)


@router.get("/google/callback")
async def google_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db)
):
    slug = None
    try:
        parts = state.split(":")
        _, intended_role, origin = parts[0], parts[1], parts[2]
        if len(parts) > 3:
            slug = parts[3] or None

        if intended_role not in ("patient", "doctor", "clinic_admin"):
            intended_role = "patient"
        if origin not in ("signup", "login"):
            origin = "signup"
    except ValueError:
        intended_role = "patient"
        origin = "signup"

    error_redirect_path = f"/{slug}/signup" if (origin == "signup" and slug) else ("/signup" if origin == "signup" else "/login")

    try:
        token_data = await exchange_code_for_token(code)
        access_token = token_data.get("access_token")

        if not access_token:
            raise HTTPException(status_code=400, detail="Google token exchange failed")

        google_user = await get_google_user_info(access_token)
        email = google_user["email"].strip().lower()
        full_name = google_user["full_name"]
        google_id = google_user["google_id"]
        picture = google_user["picture"]

        if not google_user.get("email_verified"):
            raise HTTPException(status_code=400, detail="Google email not verified")

        user = db.query(User).filter(User.email == email).first()

        if not user:
            if origin == "login":
                return RedirectResponse(
                    url=f"{settings.FRONTEND_URL}/login?error=account_not_found"
                )

            # Resolve clinic_id from slug for new Google signup
            clinic = resolve_clinic_by_slug(slug=slug, role=intended_role, db=db)
            resolved_clinic_id = clinic.clinic_id if clinic else None

            user = User(
                email=email,
                full_name=full_name,
                google_id=google_id,
                picture=picture,
                role=intended_role,
                auth_provider="google",
                is_active=True,
                password=None
            )
            db.add(user)
            db.flush()

            create_role_profile(user, db, clinic_id=resolved_clinic_id)

            db.commit()
            db.refresh(user)

        else:
            if not user.is_active:
                return RedirectResponse(url=f"{settings.FRONTEND_URL}{error_redirect_path}?error=account_deactivated")

            user.google_id = google_id
            user.picture = picture

            db.commit()
            db.refresh(user)

        jwt_token = generate_user_token(user, db)

        redirect_url = (
            f"{settings.FRONTEND_URL}/auth/callback"
            f"?token={jwt_token}&role={user.role}"
        )
        return RedirectResponse(url=redirect_url)

    except HTTPException as e:
        logger.error(f"GOOGLE OAUTH HTTPException: {e.detail}")
        db.rollback()
        return RedirectResponse(url=f"{settings.FRONTEND_URL}{error_redirect_path}?error=google_auth_failed")
    except Exception as e:
        logger.exception("GOOGLE OAUTH ERROR")
        db.rollback()
        return RedirectResponse(url=f"{settings.FRONTEND_URL}{error_redirect_path}?error=google_auth_failed")


# ════════════════════════════════════
# COMMON ROUTES
# ════════════════════════════════════

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Fetch profile info for currently logged-in user"""
    return current_user


@router.put("/update-role", response_model=UserResponse)
def update_role(
    payload: UpdateRoleRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Set role and profile for first-time Google signups"""
    current_user.role = payload.role
    db.flush()

    create_role_profile(current_user, db)

    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/change-password")
def change_password(
    old_password: str,
    new_password: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change password for email users"""

    if current_user.auth_provider == "google":
        raise HTTPException(
            status_code=400,
            detail="Google account password cannot be changed"
        )

    if not verify_password(old_password, current_user.password):
        raise HTTPException(status_code=400, detail="Old password is wrong")

    current_user.password = hash_password(new_password)
    db.commit()
    return {"message": "Password changed successfully"}