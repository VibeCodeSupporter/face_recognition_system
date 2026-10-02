from typing import Literal

from pydantic import Field, StrictBool

from app.dto.common import DTO, PageQuery, PatchDTO, text

DeviceStatus = Literal["online", "offline", "warning"]


class DeviceSettings(DTO):
    threshold: float = Field(strict=True, ge=0, le=100)
    doorDuration: int = Field(strict=True, ge=1, le=60)
    liveness: StrictBool


class DeviceCreate(DTO):
    device_code: text(50)
    name: text(100)
    location: text(200) | None = None
    status: DeviceStatus = "offline"
    settings: DeviceSettings = Field(default_factory=lambda: DeviceSettings(threshold=80, doorDuration=3, liveness=True))


class DevicePatch(PatchDTO):
    required_non_null = frozenset({"device_code", "name", "status", "settings"})
    device_code: text(50) | None = None
    name: text(100) | None = None
    location: text(200) | None = None
    status: DeviceStatus | None = None
    settings: DeviceSettings | None = None


class DeviceQuery(PageQuery):
    status: DeviceStatus | None = None
    device_code: text(50) | None = None
