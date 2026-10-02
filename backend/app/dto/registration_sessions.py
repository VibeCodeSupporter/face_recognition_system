from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import UUID

from pydantic import field_validator, model_validator

from app.dto.common import DTO, PageQuery, Timestamp

SessionStatus = Literal["pending", "completed", "cancelled", "expired", "failed"]


class SessionCreate(DTO):
    user_id: UUID
    device_id: UUID
    expires_at: Timestamp | None = None

    @field_validator("expires_at", mode="before")
    @classmethod
    def expiry_not_null(cls, value):
        if value is None:
            raise ValueError("expires_at cannot be null.")
        return value

    @model_validator(mode="after")
    def future_expiry(self):
        if self.expires_at is not None and self.expires_at <= datetime.now(timezone.utc) + timedelta(minutes=1):
            raise ValueError("Expiry must be at least one minute in the future.")
        return self


class SessionPatch(DTO):
    status: Literal["completed", "cancelled", "failed"]


class SessionQuery(PageQuery):
    user_id: UUID | None = None
    device_id: UUID | None = None
    status: SessionStatus | None = None
