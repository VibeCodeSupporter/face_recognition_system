from typing import Literal

from pydantic import model_validator

from app.dto.common import DTO, PageQuery, Timestamp, text

DeletedEntityType = Literal["user", "device", "session", "access_log"]


class DeletionHistoryQuery(PageQuery):
    entity_type: DeletedEntityType | None = None
    search: text(100) | None = None
    start_time: Timestamp | None = None
    end_time: Timestamp | None = None

    @model_validator(mode="after")
    def valid_range(self):
        if self.start_time is not None and self.end_time is not None and self.start_time > self.end_time:
            raise ValueError("start_time must be earlier than or equal to end_time.")
        return self

