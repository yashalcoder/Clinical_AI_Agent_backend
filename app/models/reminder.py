import uuid
import enum

from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SAEnum, Integer, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.database import Base


class ReminderType(str, enum.Enum):
    h24 = "24h"
    h2 = "2h"
    confirm = "confirm"


class ReminderChannel(str, enum.Enum):
    whatsapp = "whatsapp"
    sms = "sms"
    email = "email"


class ReminderStatus(str, enum.Enum):
    pending = "pending"        # created, not yet due
    queued = "queued"          # claimed by scheduler, handed to Celery
    processing = "processing"  # worker is actively sending it
    sent = "sent"               # delivered successfully
    failed = "failed"           # send failed (see error_message)
    cancelled = "cancelled"     # appointment was cancelled/rescheduled before it went out


class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    appointment_id = Column(
        UUID(as_uuid=True),
        ForeignKey("appointments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    type = Column(
        SAEnum(ReminderType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )

    channel = Column(
        SAEnum(ReminderChannel, values_callable=lambda x: [e.value for e in x]),
        default=ReminderChannel.whatsapp,
        nullable=False,
    )

    status = Column(
        SAEnum(ReminderStatus, values_callable=lambda x: [e.value for e in x]),
        default=ReminderStatus.pending,
        nullable=False,
        index=True,
    )

    scheduled_at = Column(DateTime(timezone=True), nullable=False, index=True)
    sent_at = Column(DateTime(timezone=True))

    attempt_count = Column(Integer, default=0, nullable=False)
    provider_message_id = Column(String, nullable=True)
    error_message = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        # Speeds up the scheduler's "find due reminders" query
        Index("ix_reminders_status_scheduled_at", "status", "scheduled_at"),
    )