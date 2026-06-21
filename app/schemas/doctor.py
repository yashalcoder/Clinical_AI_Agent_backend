from pydantic import BaseModel
from uuid import UUID
from datetime import time
from typing import Optional, List

class DoctorCreate(BaseModel):
    specialization: str
    qualification:  Optional[str]  = None
    fee:            Optional[float] = 0
    available_days: Optional[List[str]] = ["Mon", "Tue", "Wed", "Thu", "Fri"]
    slot_duration:  Optional[int]  = 30
    start_time:     Optional[time] = time(9, 0)
    end_time:       Optional[time] = time(17, 0)

class DoctorUpdate(BaseModel):
    specialization: Optional[str]       = None
    qualification:  Optional[str]       = None
    fee:            Optional[float]     = None
    available_days: Optional[List[str]] = None
    slot_duration:  Optional[int]       = None
    start_time:     Optional[time]      = None
    end_time:       Optional[time]      = None
    is_active:      Optional[bool]      = None

class DoctorResponse(BaseModel):
    id:             UUID
    user_id:        UUID
    specialization: str
    qualification:  Optional[str]
    fee:            Optional[float]
    available_days: Optional[List[str]]
    slot_duration:  Optional[int]
    start_time:     Optional[time]
    end_time:       Optional[time]
    is_active:      bool

    class Config:
        from_attributes = True