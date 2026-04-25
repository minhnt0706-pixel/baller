from __future__ import annotations

import uuid
from datetime import time

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CourtBase(BaseModel):
    name: str
    address: str
    district: str
    sport_type: str
    price_per_hour_vnd: int
    opening_time: time
    closing_time: time
    phone: str | None = None
    description: str | None = None


class CourtCreate(CourtBase):
    pass


class Court(CourtBase):
    id: uuid.UUID = Field(..., description="UUIDv4 court identifier")

    model_config = ConfigDict(from_attributes=True)

    @field_validator("id", mode="before")
    @classmethod
    def coerce_uuid(cls, v: object) -> uuid.UUID:
        if isinstance(v, uuid.UUID):
            return v
        return uuid.UUID(str(v))


class CourtListResponse(BaseModel):
    items: list[Court]
    total: int
    limit: int
    offset: int
