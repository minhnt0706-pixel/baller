import uuid
from datetime import time

from sqlalchemy import Column, Index, Numeric, String, Time
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from backend.db.base import Base


class Court(Base):
    __tablename__ = "courts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    name = Column(String(255), nullable=False)
    address = Column(String(500), nullable=False)
    district = Column(String(100), nullable=False, index=True)
    sport_type = Column(String(50), nullable=False, index=True)
    price_per_hour = Column(Numeric(12, 0), nullable=False)
    opening_time = Column(Time, nullable=False, default=time(6, 0))
    closing_time = Column(Time, nullable=False, default=time(22, 0))
    phone = Column(String(20), nullable=True)
    description = Column(String(1000), nullable=True)

    bookings = relationship("Booking", back_populates="court", lazy="select")

    __table_args__ = (
        Index("ix_courts_sport_type_district", "sport_type", "district"),
    )
