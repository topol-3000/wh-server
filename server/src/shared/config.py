"""Configuration management using pydantic-settings."""

from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        case_sensitive=False,
        extra="ignore",
    )

    base_domain: str = Field(description="Base domain for subdomain-based routing")
    nats_url: str = Field(description="NATS server URL")
    request_timeout: float = Field( description="Request timeout in seconds", ge=1.0)
    log_level: str = Field(description="Logging level")


@lru_cache
def get_settings() -> Settings:
    """Get the application settings instance."""
    return Settings()
