from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    SmallInteger,
    String,
    TIMESTAMP,
    text,
)
from sqlalchemy.sql import func
from app.database import Base


class Clinic(Base):
    __tablename__ = "clinic"

    clinic_id = Column(BigInteger, primary_key=True, autoincrement=True)

    clinic_name = Column(String, default="")
    payment_enabled = Column(Boolean)
    clinic_status = Column(Boolean)

    countory = Column(String)
    payment_provider = Column(String)

    email = Column(String)
    phone = Column(SmallInteger)
    address = Column(String)
    city = Column(String)
    logo = Column(String)

    stripe_payment_id = Column(SmallInteger)

    created_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at = Column(
        TIMESTAMP(timezone=True),
        onupdate=func.now(),
    )