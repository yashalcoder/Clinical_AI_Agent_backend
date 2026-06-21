from pydantic import BaseModel
from uuid import UUID
from datetime import date
from typing import Optional

# Patient profile banane ke liye
class PatientCreate(BaseModel):
    date_of_birth:           Optional[date]   = None
    gender:                  Optional[str]    = None
    blood_group:             Optional[str]    = None
    whatsapp_no:             Optional[str]    = None
    address:                 Optional[str]    = None
    emergency_contact_name:  Optional[str]    = None
    emergency_contact_phone: Optional[str]    = None

# Patient profile update
class PatientUpdate(BaseModel):
    date_of_birth:           Optional[date]   = None
    gender:                  Optional[str]    = None
    blood_group:             Optional[str]    = None
    whatsapp_no:             Optional[str]    = None
    address:                 Optional[str]    = None
    emergency_contact_name:  Optional[str]    = None
    emergency_contact_phone: Optional[str]    = None

# Response
class PatientResponse(BaseModel):
    id:                      UUID
    user_id:                 UUID
    date_of_birth:           Optional[date]
    gender:                  Optional[str]
    blood_group:             Optional[str]
    whatsapp_no:             Optional[str]
    address:                 Optional[str]
    emergency_contact_name:  Optional[str]
    emergency_contact_phone: Optional[str]

    class Config:
        from_attributes = True