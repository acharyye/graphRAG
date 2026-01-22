"""Application settings using Pydantic Settings."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # Neo4j Configuration
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "password"

    # LLM & Embeddings
    ANTHROPIC_API_KEY: str
    ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"
    VOYAGE_API_KEY: str
    VOYAGE_MODEL: str = "voyage-3"

    # API Connectors (optional for MVP - use mock data if not set)
    GOOGLE_ADS_DEVELOPER_TOKEN: str | None = None
    GOOGLE_ADS_CLIENT_ID: str | None = None
    GOOGLE_ADS_CLIENT_SECRET: str | None = None
    GOOGLE_ADS_REFRESH_TOKEN: str | None = None
    GOOGLE_ADS_LOGIN_CUSTOMER_ID: str | None = None

    META_APP_ID: str | None = None
    META_APP_SECRET: str | None = None
    META_ACCESS_TOKEN: str | None = None

    # Notifications
    SLACK_WEBHOOK_URL: str | None = None
    SENDGRID_API_KEY: str | None = None
    SENDGRID_FROM_EMAIL: str | None = None

    # Authentication
    JWT_SECRET_KEY: str = "dev-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24

    # Application Settings
    APP_NAME: str = "Marketing GraphRAG"
    APP_ENV: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # Query Settings
    CONFIDENCE_THRESHOLD: float = 0.7
    MAX_QUERY_RESULTS: int = 100
    QUERY_TIMEOUT_SECONDS: int = 30

    # Data Sync Settings
    SYNC_SCHEDULE_HOUR: int = 2  # 2 AM
    DEFAULT_DATA_RETENTION_DAYS: int = 365

    # Rate Limiting
    MAX_REQUESTS_PER_MINUTE: int = 60
    RETRY_MAX_ATTEMPTS: int = 3
    RETRY_BASE_DELAY_SECONDS: float = 1.0

    # Azure Monitor (optional)
    AZURE_MONITOR_CONNECTION_STRING: str | None = None

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def google_ads_configured(self) -> bool:
        return all([
            self.GOOGLE_ADS_DEVELOPER_TOKEN,
            self.GOOGLE_ADS_CLIENT_ID,
            self.GOOGLE_ADS_REFRESH_TOKEN,
        ])

    @property
    def meta_ads_configured(self) -> bool:
        return all([
            self.META_APP_ID,
            self.META_APP_SECRET,
            self.META_ACCESS_TOKEN,
        ])

    @property
    def slack_configured(self) -> bool:
        return self.SLACK_WEBHOOK_URL is not None

    @property
    def email_configured(self) -> bool:
        return all([self.SENDGRID_API_KEY, self.SENDGRID_FROM_EMAIL])


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
