import secrets
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User, UserRole
from app.models.patient import Patient
from app.models.doctor import Doctor
from app.schemas.auth import (
    RegisterRequest, LoginRequest, TokenResponse,
    UserResponse, UpdateRoleRequest
)
from app.core.security import (
    hash_password, verify_password,
    create_access_token, get_current_user
)
from app.core.config import settings
from app.services.google_oauth import (
    get_google_auth_url,
    exchange_code_for_token,
    get_google_user_info
)

router = APIRouter()


# ── Helper: Patient/Doctor row banao ───────────────────────
def create_role_profile(user: User, db: Session):
    """
    User ke role ke hisaab se
    patients ya doctors table mein row banao
    """
    if user.role == UserRole.patient:
        existing = db.query(Patient).filter(Patient.user_id == user.id).first()
        if not existing:
            db.add(Patient(user_id=user.id))

    elif user.role == UserRole.doctor:
        existing = db.query(Doctor).filter(Doctor.user_id == user.id).first()
        if not existing:
            db.add(Doctor(
                user_id=user.id,
                specialization="General"
            ))


# ════════════════════════════════════
# EMAIL AUTH ROUTES
# ════════════════════════════════════
from sqlalchemy.exc import IntegrityError

VALID_ROLES = {"patient", "doctor"}  # keep in sync with your schema/enum

@router.post("/register", response_model=TokenResponse, status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    """Email se naya user register karo"""

    # --- Normalize inputs ---
    email = payload.email.strip().lower()
    first_name = payload.firstName.strip()
    last_name = (payload.lastName or "").strip()
    role = (payload.role or "").strip().lower()
    phone = (payload.phone or "").strip()

    # --- Basic field validation ---
    if not first_name:
        raise HTTPException(status_code=400, detail="First name is required")

    if role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail="Invalid account role")

    if len(payload.password) < 8:
        raise HTTPException(
            status_code=400, detail="Password must be at least 8 characters"
        )

    # --- Duplicate email check (pre-check, not fully race-safe on its own) ---
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    # --- Optional: duplicate phone check ---
    if phone and db.query(User).filter(User.phone == phone).first():
        raise HTTPException(status_code=400, detail="Phone number already registered")
    first_name = payload.firstName.strip()
    last_name = (payload.lastName or "").strip()
    full_name = f"{first_name} {last_name}".strip()
    user = User(
        email=email,
        full_name=full_name,
        phone=phone,
        role=role,
        password=hash_password(payload.password),
        auth_provider="email",
    )

    try:
        db.add(user)
        db.flush()

        # Role profile banao
        create_role_profile(user, db)

        db.commit()
    except IntegrityError:
        # Handles race condition: two concurrent signups with same email
        db.rollback()
        raise HTTPException(status_code=400, detail="Email already registered")
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500, detail="Could not create account, please try again"
        )

    db.refresh(user)

    token = create_access_token(
        data={"sub": str(user.id), "role": user.role, "email": user.email}
    )
    return TokenResponse(
        access_token=token,
        role=user.role,
        user_id=user.id,
        full_name=user.full_name,
        is_new_user=True
        # picture=user.picture
    )

# POST /api/auth/login
@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """Email + password se login karo"""

    user = db.query(User).filter(User.email == payload.email).first()

    # User nahi mila ya password galat
    if not user or not user.password:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not verify_password(payload.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Google se register tha — password nahi set kiya
    if user.auth_provider == "google":
        raise HTTPException(
            status_code=400,
            detail="This account uses Google login. Please use 'Login with Google'."
        )

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account deactivated")

    token = create_access_token(data={
        "sub":   str(user.id),
        "role":  user.role,
        "email": user.email
    })

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

# GET /api/auth/google
# GET /api/auth/google
@router.get("/google")
def google_login(
    role: str = Query("patient"),
    origin: str = Query("signup")  # "signup" ya "login"
):
    if role not in ("patient", "clinic"):
        role = "patient"
    if origin not in ("signup", "login"):
        origin = "signup"

    # state mein role + origin dono pack karo
    raw_token = secrets.token_urlsafe(16)
    state = f"{raw_token}:{role}:{origin}"

    auth_url = get_google_auth_url(state=state)
    return RedirectResponse(url=auth_url)
import logging
logger = logging.getLogger(__name__)
# GET /api/auth/google/callback

@router.get("/google/callback")
async def google_callback(
    code:  str = Query(...),
    state: str = Query(...),
    db:    Session = Depends(get_db)
):
    # State parse karo pehle hi — taaki error case mein bhi origin pata ho
    try:
        _, intended_role, origin = state.split(":", 2)
        if intended_role not in ("patient", "doctor"):
            intended_role = "patient"
        if origin not in ("signup", "login"):
            origin = "signup"
    except ValueError:
        intended_role = "patient"
        origin = "signup"

    error_redirect_path = "/signup" if origin == "signup" else "/login"

    try:
        token_data   = await exchange_code_for_token(code)
        access_token = token_data.get("access_token")

        if not access_token:
            raise HTTPException(status_code=400, detail="Google token exchange failed")

        google_user = await get_google_user_info(access_token)
        email     = google_user["email"].strip().lower()
        full_name = google_user["full_name"]
        google_id = google_user["google_id"]
        picture   = google_user["picture"]

        if not google_user.get("email_verified"):
            raise HTTPException(status_code=400, detail="Google email not verified")

        user = db.query(User).filter(User.email == email).first()

        if not user:
            # Account exist nahi karta
            if origin == "login":
                # Login page se try kiya, lekin koi account hai hi nahi — signup karne bhejo
                return RedirectResponse(
                    url=f"{settings.FRONTEND_URL}/login?error=account_not_found"
                )

            # Signup flow — naya user banao (role signup page se explicitly aaya hai)
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

            if intended_role == "doctor":
                db.add(Doctor(user_id=user.id, specialization="General"))
            else:
                db.add(Patient(user_id=user.id))

            db.commit()
            db.refresh(user)

        else:
            # Existing user mila — chahe email se bana ho ya google se, ab link/refresh karo
            if not user.is_active:
                return RedirectResponse(url=f"{settings.FRONTEND_URL}{error_redirect_path}?error=account_deactivated")

            # Google ne is email ko verify kar diya hai, isliye safely link kar sakte hain
            user.google_id = google_id
            user.picture   = picture

            db.commit()
            db.refresh(user)

        jwt_token = create_access_token(data={
            "sub": str(user.id), "role": user.role, "email": user.email
        })

        redirect_url = (
            f"{settings.FRONTEND_URL}/auth/callback"
            f"?token={jwt_token}&role={user.role}"
        )
        return RedirectResponse(url=redirect_url)

    except HTTPException as e:
        print("=" * 60)
        print("GOOGLE OAUTH HTTPException:", e.detail)
        print("=" * 60)
        db.rollback()
        return RedirectResponse(url=f"{settings.FRONTEND_URL}{error_redirect_path}?error=google_auth_failed")
    except Exception as e:
        import traceback
        print("=" * 60)
        print("GOOGLE OAUTH ERROR:", type(e).__name__, "-", str(e))
        traceback.print_exc()
        print("=" * 60)
        db.rollback()
        return RedirectResponse(url=f"{settings.FRONTEND_URL}{error_redirect_path}?error=google_auth_failed")
# ════════════════════════════════════
# COMMON ROUTES
# ════════════════════════════════════

# GET /api/auth/me
@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Apni info dekho"""
    return current_user


# PUT /api/auth/update-role
@router.put("/update-role", response_model=UserResponse)
def update_role(
    payload:      UpdateRoleRequest,
    current_user: User    = Depends(get_current_user),
    db:           Session = Depends(get_db)
):
    """
    Google se pehli baar aane ke baad role select karo
    Frontend is_new_user=true ho to yeh call kare
    """
    current_user.role = payload.role
    db.flush()

    # Role ke hisaab se profile banao
    create_role_profile(current_user, db)

    db.commit()
    db.refresh(current_user)
    return current_user


# POST /api/auth/change-password
@router.post("/change-password")
def change_password(
    old_password: str,
    new_password: str,
    current_user: User    = Depends(get_current_user),
    db:           Session = Depends(get_db)
):
    """Password badlo — sirf email users ke liye"""

    if current_user.auth_provider == "google":
        raise HTTPException(
            status_code=400,
            detail="Google account ka password change nahi ho sakta"
        )

    if not verify_password(old_password, current_user.password):
        raise HTTPException(status_code=400, detail="Old password is wrong")

    current_user.password = hash_password(new_password)
    db.commit()
    return {"message": "Password changed successfully"}