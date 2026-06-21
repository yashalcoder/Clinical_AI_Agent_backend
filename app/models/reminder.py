import uuid
import enum
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.database import Base

class ReminderType(str, enum.Enum):
    h24     = "24h"
    h2      = "2h"
    confirm = "confirm"

class ReminderChannel(str, enum.Enum):
    whatsapp = "whatsapp"
    sms      = "sms"

class ReminderStatus(str, enum.Enum):
    pending = "pending"
    sent    = "sent"
    failed  = "failed"

class Reminder(Base):
    __tablename__ = "reminders"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    appointment_id = Column(UUID(as_uuid=True), ForeignKey("appointments.id", ondelete="CASCADE"), nullable=False)
    type           = Column(SAEnum(ReminderType), nullable=False)
    channel        = Column(SAEnum(ReminderChannel), default=ReminderChannel.whatsapp)
    status         = Column(SAEnum(ReminderStatus), default=ReminderStatus.pending)
    scheduled_at   = Column(DateTime(timezone=True), nullable=False)
    sent_at        = Column(DateTime(timezone=True))
    error_message  = Column(String)
    created_at     = Column(DateTime(timezone=True), server_default=func.now())