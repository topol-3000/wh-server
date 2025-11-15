"""Configuration management using pydantic-settings."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="WH_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    host: str = Field(default="0.0.0.0", description="Server bind address")
    port: int = Field(default=8080, description="Server port", ge=1, le=65535)
    base_domain: str = Field(default="localhost", description="Base domain for subdomain-based routing")
    nats_url: str = Field(default="nats://localhost:4222", description="NATS server URL")
    request_timeout: float = Field(default=30.0, description="Request timeout in seconds", ge=1.0)
    log_level: str = Field(default="INFO", description="Logging level")
