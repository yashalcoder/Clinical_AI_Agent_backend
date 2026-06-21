from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Supabase PostgreSQL se connect karo
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,       # connection check karta hai
    pool_size=5,              # 5 connections ready rakho
    max_overflow=10,          # zaroorat pe 10 extra
    echo=settings.DEBUG       # SQL queries terminal mein dikhao (dev only)
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()

# FastAPI dependency — har request ke liye DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
        print("DB session closed successfully.")
    finally:
        db.close()


