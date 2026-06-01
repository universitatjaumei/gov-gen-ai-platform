"""
Server core configuration.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parents[2] / ".env")


@dataclass(frozen=True)
class Settings:
    jwt_secret_key: str
    jwt_algorithm: str
    jwt_expiration_minutes: int
    environment: str
    # Sandbox (script-sandbox microservice — SBX.1/SBX.2)
    sandbox_base_url: str = "http://script-sandbox:5000"
    sandbox_timeout_seconds_default: int = 30
    sandbox_connect_timeout_seconds: float = 5.0
    sandbox_max_retries_on_connect_error: int = 1
    sandbox_mode: str = "http"

    @property
    def is_dev_mode(self) -> bool:
        return self.environment == "development"


def get_settings() -> Settings:
    secret = os.environ.get("JWT_SECRET_KEY")
    if not secret:
        raise RuntimeError("JWT_SECRET_KEY environment variable is required")
    # sandbox_mode defaults to "local" when TESTING=1 to avoid Docker dependency in CI.
    default_sandbox_mode = "local" if os.getenv("TESTING") == "1" else "http"
    return Settings(
        jwt_secret_key=secret,
        jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
        jwt_expiration_minutes=int(os.getenv("JWT_EXPIRATION_MINUTES", "60")),
        environment=os.getenv("ENVIRONMENT", "development"),
        sandbox_base_url=os.getenv("SANDBOX_BASE_URL", "http://script-sandbox:5000"),
        sandbox_timeout_seconds_default=int(os.getenv("SANDBOX_TIMEOUT_SECONDS_DEFAULT", "30")),
        sandbox_connect_timeout_seconds=float(os.getenv("SANDBOX_CONNECT_TIMEOUT_SECONDS", "5.0")),
        sandbox_max_retries_on_connect_error=int(
            os.getenv("SANDBOX_MAX_RETRIES_ON_CONNECT_ERROR", "1")
        ),
        sandbox_mode=os.getenv("SANDBOX_MODE", default_sandbox_mode),
    )
