from datetime import datetime
from uuid import UUID
from typing import Optional
from pydantic import BaseModel, EmailStr,Field
from datetime import time
from decimal import Decimal


class CreateDoctorInviteRequest(BaseModel):
    email: EmailStr
    specialization: Optional[str] = None


class DoctorInviteResponse(BaseModel):
    id: UUID
    email: str
    specialization: Optional[str]
    status: str
    expires_at: datetime
    invite_url: str

    class Config:
        from_attributes = True


class InvitePreviewResponse(BaseModel):
    email: str
    specialization: Optional[str]
    clinic_name: str



class AcceptInviteRequest(BaseModel):
    # User fields
    full_name: str
    password: str

    # Doctor fields
    qualification: str
    fee: Decimal = Field(default=0, ge=0)

    available_days: list[str] = Field(
        default_factory=lambda: [
            "Mon",
            "Tue",
            "Wed",
            "Thu",
            "Fri",
        ]
    )

    slot_duration: int = Field(default=30, gt=0)

    start_time: time = time(9, 0)
    end_time: time = time(17, 0)

