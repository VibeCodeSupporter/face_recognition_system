import sys

from app.config import ConfigurationError, load_settings
from app.errors import AppError
from app.infrastructure.database import Database


def main() -> int:
    database = None
    try:
        database = Database(load_settings(require_api_key=False))
        for item in database.check():
            print(f"[OK] public.{item['table']}")
        print("Database connection and MVP columns verified. No row data was returned or changed.")
        return 0
    except (ConfigurationError, AppError) as error:
        print(f"[DATABASE] {error}", file=sys.stderr)
        return 1
    finally:
        if database is not None:
            database.close()


if __name__ == "__main__":
    sys.exit(main())
