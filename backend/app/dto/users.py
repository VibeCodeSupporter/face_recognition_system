from typing import Literal

from pydantic import ConfigDict, EmailStr, Field

from app.dto.common import DTO, PageQuery, PatchDTO, text

UserStatus = Literal["active", "inactive"]
Email = EmailStr


class UserCreate(DTO):
    model_config = ConfigDict(json_schema_extra={"example": {
        "user_code": "NV001", "full_name": "Nguyen Van An",
    }})
    user_code: text(50)
    full_name: text(150)
    email: Email | None = Field(default=None, max_length=150)
    phone: text(20) | None = None
    department: text(100) | None = None
    role: text(50) | None = None
    status: UserStatus = "active"



class UserPatch(PatchDTO):
    model_config = ConfigDict(json_schema_extra={"example": {"full_name": "Nguyen Van An Updated"}})
    required_non_null = frozenset({"user_code", "full_name", "status"})
    user_code: text(50) | None = None
    full_name: text(150) | None = None
    email: Email | None = Field(default=None, max_length=150)
    phone: text(20) | None = None
    department: text(100) | None = None
    role: text(50) | None = None
    status: UserStatus | None = None



class UserQuery(DTO):
    status: UserStatus | None = None
    # user_code: text(50) | None = None
    department: text(100) | None = None
    
