class AppError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


def database_error(code: str) -> AppError:
    errors = {
        "23505": (409, "DUPLICATE", "A record with this unique identifier already exists."),
        "23503": (409, "REFERENCE_CONFLICT", "A referenced record is missing or this record is still in use."),
        "23514": (422, "CONSTRAINT_VIOLATION", "The record violates a database constraint."),
        "23502": (422, "REQUIRED_FIELD", "A required database field is missing."),
        "22001": (422, "VALUE_TOO_LONG", "A field exceeds its database length limit."),
        "22P02": (422, "INVALID_VALUE", "A field has an invalid database value."),
        "22007": (422, "INVALID_TIMESTAMP", "A timestamp has an invalid database format."),
        "22008": (422, "INVALID_TIMESTAMP", "A timestamp is outside the database range."),
    }
    return AppError(*errors.get(code, (503, "DATABASE_UNAVAILABLE", "The database request could not be completed.")))
