import uuid
import enum

from sqlalchemy import Column, String, ForeignKey,BigInteger, TIMESTAMP, Enum as SAEnum,DateTime
from sqlalchemy.dialects.postgresql import UUID,BIGINT
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base

class DoctorInviteStatus(str, enum.Enum):
    pending  = "pending"
    accepted = "accepted"
    expired  = "expired"


class DoctorInvite(Base):
    __tablename__ = "doctor_invites"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    clinic_id = Column(BigInteger, ForeignKey("clinic.clinic_id", ondelete="CASCADE"), nullable=False)


    email = Column(String, nullable=False, index=True)
    specialization = Column(String)

    token = Column(String, unique=True, nullable=False, index=True)

    status = Column(
        SAEnum(
            DoctorInviteStatus,
            values_callable=lambda x: [e.value for e in x]
        ),
        default=DoctorInviteStatus.pending,
        nullable=False,
    )

    expires_at = Column(
        DateTime(timezone=True),
        nullable=False,
    )

    created_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        onupdate=func.now(),
    )

    # Relationships
    clinic = relationship("Clinic", backref="doctor_invites")