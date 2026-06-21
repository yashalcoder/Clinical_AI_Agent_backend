from pydantic import BaseModel
from uuid import UUID
from datetime import date, datetime
from typing import Optional, List

# Prescription item
class PrescriptionItem(BaseModel):
    medicine: str
    dosage:   str
    times:    str
    days:     int

# Record create karne ke liye
class MedicalRecordCreate(BaseModel):
    appointment_id: Optional[UUID]            = None
    symptoms:       Optional[str]             = None
    diagnosis:      Optional[str]             = None
    prescriptions:  Optional[List[PrescriptionItem]] = []
    follow_up_date: Optional[date]            = None

# Record update
class MedicalRecordUpdate(BaseModel):
    symptoms:       Optional[str]             = None
    diagnosis:      Optional[str]             = None
    prescriptions:  Optional[List[PrescriptionItem]] = None
    follow_up_date: Optional[date]            = None
    voice_note_url: Optional[str]             = None

# Response
class MedicalRecordResponse(BaseModel):
    id:             UUID
    appointment_id: Optional[UUID]
    patient_id:     UUID
    doctor_id:      UUID
    symptoms:       Optional[str]
    diagnosis:      Optional[str]
    prescriptions:  Optional[list]
    voice_note_url: Optional[str]
    follow_up_date: Optional[date]
    created_at:     datetime

    class Config:
        from_attributes = True