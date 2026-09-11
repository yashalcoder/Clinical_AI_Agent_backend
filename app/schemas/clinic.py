from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


# ── Request: Super Admin creates a new clinic ───────────────────────────────
class CreateClinicRequest(BaseModel):
    clinic_name: str
    city: Optional[str] = None
    address: Optional[str] = None
    whatsapp_number: Optional[str] = None

    admin_name: Optional[str] = None
    admin_email: EmailStr

    plan: Optional[str] = "Growth"   # "Starter" | "Growth" | "Pro / Network"


# ── Response: returned right after a clinic is created ──────────────────────
# Matches what AddClinicModal's success screen expects.
class ClinicResponse(BaseModel):
    id: int
    name: str
    slug: str
    adminEmail: str
    bookingUrl: str

    class Config:
        from_attributes = True


# ── Response: one row in the Super Admin "Clinics" list ─────────────────────
class ClinicListItem(BaseModel):
    id: int
    name: str
    city: Optional[str]
    status: str                  # "active" | "trial" | "suspended"
    doctor_count: int
    patient_count: int

    class Config:
        from_attributes = True


# ── Response: full clinic detail view (Super Admin → Clinic Detail page) ───
class ClinicDetailResponse(BaseModel):
    id: int
    name: str
    city: Optional[str]
    address: Optional[str]
    whatsapp_number: Optional[str]
    status: str
    plan: Optional[str]
    booking_url: str
    doctor_count: int
    patient_count: int
    appointments_this_month: int
    created_at: datetime

    class Config:
        from_attributes = True


# ── Request: Super Admin suspends/reactivates a clinic ──────────────────────
class UpdateClinicStatusRequest(BaseModel):
    status: str   # "active" | "trial" | "suspended"


# ── Request: Clinic Admin edits their own clinic profile ────────────────────
class UpdateClinicProfileRequest(BaseModel):
    clinic_name: Optional[str] = None
    city: Optional[str] = None
    address: Optional[str] = None
    whatsapp_number: Optional[str] = None
    logo: Optional[str] = None