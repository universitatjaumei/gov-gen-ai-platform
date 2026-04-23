"""
Server core configuration.
"""
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    jwt_secret_key: str
    jwt_algorithm: str
    jwt_expiration_minutes: int
    environment: str

    @property
    def is_dev_mode(self) -> bool:
        return self.environment == "development"


def get_settings() -> Settings:
    secret = os.environ.get("JWT_SECRET_KEY")
    if not secret:
        raise RuntimeError("JWT_SECRET_KEY environment variable is required")
    return Settings(
        jwt_secret_key=secret,
        jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
        jwt_expiration_minutes=int(os.getenv("JWT_EXPIRATION_MINUTES", "60")),
        environment=os.getenv("ENVIRONMENT", "development"),
    )
