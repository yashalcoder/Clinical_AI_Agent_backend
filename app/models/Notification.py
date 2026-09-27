import uuid

from sqlalchemy import (
    Column,
    String,
    Boolean,
    BigInteger,
    DateTime,
    ForeignKey,
    func,
)
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    clinic_id = Column(
        BigInteger,
        nullable=True,
        index=True,
    )

    type = Column(
        String,
        nullable=False,
    )

    title = Column(
        String,
        nullable=False,
    )

    body = Column(
        String,
        nullable=True,
    )

    link = Column(
        String,
        nullable=True,
    )

    is_read = Column(
        Boolean,
        default=False,
        nullable=False,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )