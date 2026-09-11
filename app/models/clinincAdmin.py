from sqlalchemy import BigInteger, Column, ForeignKey, TIMESTAMP
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class ClinicAdmin(Base):
    __tablename__ = "clinic_admins"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    clinic_id = Column(BigInteger, ForeignKey("clinic.clinic_id", ondelete="CASCADE"), nullable=False)

    created_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        onupdate=func.now(),
    )

    user = relationship("User", backref="clinic_admins")
    clinic = relationship("Clinic", backref="admins")