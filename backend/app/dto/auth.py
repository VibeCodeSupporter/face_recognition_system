from app.dto.common import DTO, text


class LoginRequest(DTO):
    username: text(100)
    password: text(100)


class AdminProfile(DTO):
    username: str
    full_name: str
    role: str
