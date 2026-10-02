import re
from datetime import datetime, timezone
from typing import Annotated, ClassVar

from pydantic import AfterValidator, AwareDatetime, BaseModel, BeforeValidator, ConfigDict, Field, StringConstraints, field_validator, model_validator


def text(max_length: int):
    return Annotated[str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=max_length)]


def iso_input(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})", value):
        raise ValueError("Use an ISO datetime string with timezone.")
    return value


def normalize_time(value: datetime) -> datetime:
    value = value.astimezone(timezone.utc)
    return value.replace(microsecond=(value.microsecond // 1000) * 1000)


Timestamp = Annotated[AwareDatetime, BeforeValidator(iso_input), AfterValidator(normalize_time)]


class DTO(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, allow_inf_nan=False)

    def payload(self) -> dict:
        return self.model_dump(mode="json", exclude_unset=True)


class ErrorDetail(BaseModel):
    path: str
    message: str


class ErrorBody(BaseModel):
    code: str
    message: str
    request_id: str
    details: list[ErrorDetail] | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody


class PatchDTO(DTO):
    required_non_null: ClassVar[frozenset[str]] = frozenset()

    @model_validator(mode="after")
    def check_patch(self):
        if not self.model_fields_set:
            raise ValueError("At least one editable field is required.")
        if any(getattr(self, name) is None for name in self.required_non_null & self.model_fields_set):
            raise ValueError("Required fields cannot be set to null.")
        return self


class PageQuery(DTO):
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0, le=100000)

    @field_validator("limit", "offset", mode="before")
    @classmethod
    def integer_only(cls, value):
        if isinstance(value, str) and re.fullmatch(r"[0-9]+", value):
            return int(value)
        if type(value) is int:
            return value
        raise ValueError("Use a nonnegative integer.")

    def pagination(self) -> dict:
        return self.model_dump(mode="json", exclude_none=True)
