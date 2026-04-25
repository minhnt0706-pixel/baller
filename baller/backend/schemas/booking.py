from __future__ import annotations

import uuid
from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class BookingCreate(BaseModel):
    court_id: uuid.UUID
    booking_date: date
    start_time: time
    end_time: time
    booker_phone: str = Field(..., min_length=9, max_length=15)
    booker_name: str = Field(..., min_length=1, max_length=128)

    @field_validator("booker_phone")
    @classmethod
    def phone_digits_only(cls, v: str) -> str:
        stripped = v.lstrip("+")
        if not stripped.isdigit():
            raise ValueError("booker_phone must contain only digits (and optional leading +)")
        return v

    @field_validator("end_time")
    @classmethod
    def end_after_start(cls, v: time, info) -> time:
        start = info.data.get("start_time")
        if start is not None and v <= start:
            raise ValueError("end_time must be after start_time")
        return v


class BookingResponse(BaseModel):
    booking_id: uuid.UUID
    status: Literal["pending_payment", "confirmed"]
    qr_code_payload: str | None = None
    qr_code_png_base64: str | None = None
    total_amount_vnd: int
    expires_at: datetime

    model_config = {"from_attributes": True}
