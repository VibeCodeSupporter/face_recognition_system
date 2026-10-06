from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from app.dto.common import DTO, PageQuery, Timestamp

LogResult = Literal["granted", "denied"]


class AccessLogCreate(DTO):
    id: UUID
    user_id: UUID | None = None
    device_id: UUID
    result: LogResult
    confidence: float | None = Field(default=None, strict=True, ge=0, le=100)
    access_time: Timestamp

    @model_validator(mode="after")
    def recognized_grant(self):
        if self.result == "granted" and self.user_id is None:
            raise ValueError("Granted access requires a recognized user.")
        return self


class AccessLogQuery(PageQuery):
    user_id: UUID | None = None
    device_id: UUID | None = None
    result: LogResult | None = None
