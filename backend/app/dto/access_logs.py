from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from app.dto.common import DTO, PageQuery, Timestamp

LogResult = Literal["granted", "denied"]


class AccessLogCreate(DTO):
    id: UUID
    user_id: str | None = None
    device_id: UUID
    result: LogResult
    confidence: float | None = Field(default=None, strict=True, ge=0, le=100)
    access_time: Timestamp

    @model_validator(mode="after")
    def recognized_grant(self):
        if self.result == "granted" and not self.user_id:
            raise ValueError("Granted access requires a recognized user.")
        return self


class AccessLogQuery(PageQuery):
    user_id: UUID | None = None
    device_id: UUID | None = None
    result: LogResult | None = None
    start_time: Timestamp | None = None
    end_time: Timestamp | None = None

    @model_validator(mode="after")
    def valid_range(self):
        if self.start_time is not None and self.end_time is not None and self.start_time > self.end_time:
            raise ValueError("start_time must be earlier than or equal to end_time.")
        return self


class AccessLogDeleteQuery(DTO):
    start_time: Timestamp
    end_time: Timestamp
    result: LogResult | None = None
    device_id: UUID | None = None
    user_id: UUID | None = None

    @model_validator(mode="after")
    def valid_range(self):
        if self.start_time > self.end_time:
            raise ValueError("start_time must be earlier than or equal to end_time.")
        return self
