# scripts/create_superadmin.py
# Run karein terminal se: python -m scripts.create_superadmin

import sys
from app.database import SessionLocal
from app.models.user import User
from app.core.security import hash_password

def create_superadmin(email: str, password: str, name: str):
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            print(f"User with email {email} already exists.")
            return

        admin = User(
            email=email,
            password=hash_password(password),
            full_name=name,
            role="platform_admin",
        )
        db.add(admin)
        db.commit()
        print(f"Super Admin created: {email}")
    finally:
        db.close()

if __name__ == "__main__":
    create_superadmin(
        email="team32314@gmail.com",
        password="SuperAdmin@09876",
        name="NeuroTank",
    )