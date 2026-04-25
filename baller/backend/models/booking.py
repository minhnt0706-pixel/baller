import uuid
from datetime import date, datetime, time

from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from backend.db.base import Base


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    court_id = Column(
        UUID(as_uuid=True),
        ForeignKey("courts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    booking_date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    booker_name = Column(String(255), nullable=False)
    booker_phone = Column(String(20), nullable=False)
    status = Column(
        String(32),
        nullable=False,
        default="pending_payment",
    )
    total_amount_vnd = Column(Integer, nullable=False)
    qr_code_payload = Column(String(2048), nullable=True)
    qr_code_png_base64 = Column(String, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    court = relationship("Court", back_populates="bookings")

    __table_args__ = (
        UniqueConstraint(
            "court_id",
            "booking_date",
            "start_time",
            name="uq_bookings_court_date_start",
        ),
        CheckConstraint(
            "end_time > start_time",
            name="ck_bookings_end_after_start",
        ),
        CheckConstraint(
            "status IN ('pending_payment', 'confirmed', 'cancelled', 'expired')",
            name="ck_bookings_status",
        ),
        Index(
            "ix_bookings_court_date",
            "court_id",
            "booking_date",
        ),
        Index(
            "ix_bookings_status_expires",
            "status",
            "expires_at",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<Booking id={self.id} court_id={self.court_id} "
            f"date={self.booking_date} {self.start_time}-{self.end_time} "
            f"status={self.status}>"
        )
