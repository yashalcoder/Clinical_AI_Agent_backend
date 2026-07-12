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

# POST /api/auth/register
@router.post("/register", response_model=UserResponse, status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    """Email se naya user register karo"""

    # Email already hai?
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    # User banao
    user = User(
        email=payload.email,
        full_name=payload.full_name,
        phone=payload.phone,
        role=payload.role,
        password=hash_password(payload.password),
        auth_provider="email"
    )
    db.add(user)
    db.flush()

    # Role profile banao
    create_role_profile(user, db)

    db.commit()
    db.refresh(user)
    return user


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
@router.get("/google")
def google_login():
    """
    Google login page pe redirect karo
    Frontend yeh URL call kare jab user
    'Login with Google' click kare
    """
    # CSRF protection ke liye random state
    state = secrets.token_urlsafe(32)

    # Google ka auth URL banao
    auth_url = get_google_auth_url(state=state)

    # User ko Google pe bhejo
    return RedirectResponse(url=auth_url)


# GET /api/auth/google/callback
@router.get("/google/callback")
async def google_callback(
    code:  str = Query(..., description="Google ka auth code"),
    state: str = Query(..., description="CSRF state"),
    db:    Session = Depends(get_db)
):
    """
    Google yahan wapas aata hai code ke saath
    
    Flow:
    code → access_token → user_info → JWT → frontend redirect
    """

    try:
        # 1. Code se access_token lo
        token_data   = await exchange_code_for_token(code)
        access_token = token_data.get("access_token")

        if not access_token:
            raise HTTPException(status_code=400, detail="Google token exchange failed")

        # 2. access_token se user info lo
        google_user = await get_google_user_info(access_token)

        email     = google_user["email"]
        full_name = google_user["full_name"]
        google_id = google_user["google_id"]
        picture   = google_user["picture"]

        # 3. Email verified check
        if not google_user.get("email_verified"):
            raise HTTPException(status_code=400, detail="Google email not verified")

        # 4. User already DB mein hai?
        user = db.query(User).filter(User.email == email).first()
        is_new_user = False

        if not user:
            # 5. Naya user — register karo
            is_new_user = True
            user = User(
                email=email,
                full_name=full_name,
                google_id=google_id,
                picture=picture,
                role=UserRole.patient,    # default — frontend role screen dikhayega
                auth_provider="google",
                is_active=True,
                password=None             # Google user ka password nahi hota
            )
            db.add(user)
            db.flush()

            # Default patient row banao
            db.add(Patient(user_id=user.id))
            db.commit()
            db.refresh(user)

        else:
            # 6. Existing user — google_id aur picture update karo
            user.google_id = google_id
            user.picture   = picture
            db.commit()
            db.refresh(user)

        # 7. JWT token banao (same jo email login pe banta hai)
        jwt_token = create_access_token(data={
            "sub":   str(user.id),
            "role":  user.role,
            "email": user.email
        })

        # 8. Frontend ko redirect karo
        # is_new_user=true ho to frontend role select screen dikhaye
        redirect_url = (
            f"{settings.FRONTEND_URL}/auth/callback"
            f"?token={jwt_token}"
            f"&role={user.role}"
            f"&is_new_user={str(is_new_user).lower()}"
        )
        return RedirectResponse(url=redirect_url)

    except HTTPException:
        raise
    except Exception as e:
        # Error pe frontend login page pe wapas bhejo
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/login?error=google_auth_failed"
        )


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