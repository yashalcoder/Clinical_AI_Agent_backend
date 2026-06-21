from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional
from app.models.reminder import ReminderType, ReminderChannel, ReminderStatus

class ReminderResponse(BaseModel):
    id:             UUID
    appointment_id: UUID
    type:           ReminderType
    channel:        ReminderChannel
    status:         ReminderStatus
    scheduled_at:   datetime
    sent_at:        Optional[datetime]

    class Config:
        from_attributes = True