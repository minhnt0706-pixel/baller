"""
Slot model — represents a 30-minute time slot for a court on a given date.

This is a derived/computed construct (not a persisted table) used by the
GET /api/v1/courts/{court_uuid}/slots endpoint. It is represented as a
Pydantic v2 model so it can be serialised directly to JSON.
"""

from __future__ import annotations

import datetime

from pydantic import BaseModel, ConfigDict, field_serializer


class Slot(BaseModel):
    """A single 30-minute availability slot for a court."""

    model_config = ConfigDict(frozen=True)

    start_time: datetime.time
    end_time: datetime.time
    available: bool

    @field_serializer("start_time", "end_time")
    def _serialize_time(self, value: datetime.time) -> str:  # noqa: PLR6301
        """Return HH:MM string (no seconds, no microseconds)."""
        return value.strftime("%H:%M")
