from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy import text
from app.core.config import settings
from app.database import engine
from app.routes import appointments, auth
from app.routes import auth, patients, doctors, voice
app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Session middleware — Google OAuth ke liye zaroori
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY
)

# CORS — Next.js frontend allow karo
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        settings.FRONTEND_URL
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(auth.router,     prefix="/api/auth",     tags=["Auth"])
app.include_router(patients.router, prefix="/api/patients", tags=["Patients"])
app.include_router(doctors.router,  prefix="/api/doctors",  tags=["Doctors"])
app.include_router(appointments.router, prefix="/api/appointments", tags=["Appointments"])  # ← add
app.include_router(voice.router, prefix="/api/voice", tags=["Voice"])

# Sab routes include karo
# app.include_router(auth.router,         prefix="/api/auth",         tags=["Auth"])
# app.include_router(appointments.router, prefix="/api/appointments", tags=["Appointments"])
# app.include_router(patients.router,     prefix="/api/patients",     tags=["Patients"])
# app.include_router(doctors.router,      prefix="/api/doctors",      tags=["Doctors"])
# app.include_router(whatsapp.router,     prefix="/api/whatsapp",     tags=["WhatsApp"])
# app.include_router(reminders.router,    prefix="/api/reminders",    tags=["Reminders"])
# app.include_router(admin.router,        prefix="/api/admin",        tags=["Admin"])

@app.get("/")
def root():
    return {"message": f"{settings.APP_NAME} ✅ Running"}

@app.get("/health")
def health():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected ✅"}
    except Exception as e:
        return {"status": "unhealthy", "database": f"❌ {str(e)}"}