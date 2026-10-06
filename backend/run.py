import sys

import uvicorn

from app.config import ConfigurationError, load_settings
from app.main import create_app


def main() -> int:
    try:
        settings = load_settings()
        application = create_app(settings)
    except ConfigurationError as error:
        print(f"[CONFIG] {error}", file=sys.stderr)
        return 1
    uvicorn.run(application, host=settings.host, port=settings.port, server_header=False, access_log=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
