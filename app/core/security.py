from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.config import settings
from app.database import get_db
from app.models import clinincAdmin,User
# bcrypt setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Token kahan se aayega
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# ── Password ────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ── JWT ─────────────────────────────────────────────────────

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode.update({"exp": expire})
    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )


# ── Dependencies ─────────────────────────────────────────────

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    from app.models.user import User

    payload = decode_token(token)
    user_id = payload.get("sub")

    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account deactivated")

    return user


def get_current_doctor(current_user=Depends(get_current_user)):
    if current_user.role != "doctor":
        raise HTTPException(status_code=403, detail="Doctors only")
    return current_user

def get_current_patient(current_user=Depends(get_current_user)):
    if current_user.role != "patient":
        raise HTTPException(status_code=403, detail="Patients only")
    return current_user


def get_current_admin(current_user= Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role not in ("admin", "platform_admin"):
        raise HTTPException(403, "Access denied")
    
    if current_user.role == "platform_admin":
        return current_user, None  # no clinic restriction
    
    clinic_admin = db.query(clinincAdmin).filter(clinincAdmin.user_id == current_user.id).first()
    if not clinic_admin:
        raise HTTPException(404, "Clinic admin profile not found")
    return current_user, clinic_admin.clinic_id

def get_current_platform_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    Role-check dependency — runs BEFORE the route body executes.
    Only platform_admin (Super Admin) can pass through.
    """
    if current_user.role != "platform_admin":
        raise HTTPException(status_code=403, detail="Access denied")
    return current_user
 