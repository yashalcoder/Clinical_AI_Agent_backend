from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.routes import auth, appointments, patients, doctors, whatsapp, reminders, admin

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    docs_url="/docs",       # localhost:8000/docs
    redoc_url="/redoc"
)

# CORS — Next.js frontend allow karo
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    return {"message": "ClinicFlow AI Backend Running ✅"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "app": settings.APP_NAME}