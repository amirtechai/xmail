"""Application configuration loaded from environment variables / .env file."""

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application
    app_env: str = Field(default="development")
    debug: bool = Field(default=False)
    domain: str = Field(default="xmail.amirtech.ai")
    frontend_url: str = Field(default="https://xmail.amirtech.ai")
    api_url: str = Field(default="https://xmail.amirtech.ai/api")

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://xmail_user:xmail_password@postgres:5432/xmail_db"
    )

    # Redis
    redis_url: str = Field(default="redis://redis:6379/0")

    # Security
    secret_key: str = Field(default="change-me-in-production")
    jwt_algorithm: str = Field(default="HS256")
    jwt_expiration_hours: int = Field(default=24)

    # Admin
    admin_email: str = Field(default="patron@amirtech.ai")
    admin_password_hash: str = Field(default="")

    # Logging
    log_level: str = Field(default="INFO")
    log_format: str = Field(default="json")

    # Email / Compliance
    smtp_from_email: str = Field(default="outreach@xmail.amirtech.ai")
    company_physical_address: str = Field(default="")
    unsubscribe_base_url: str = Field(default="https://xmail.amirtech.ai/u")

    # Scheduling
    timezone: str = Field(default="Europe/Istanbul")
    daily_report_hour: int = Field(default=9)
    daily_report_minute: int = Field(default=0)

    # Third-party enrichment / verification
    zerobounce_api_key: str = Field(default="")
    hunter_api_key: str = Field(default="")
    proxycurl_api_key: str = Field(default="")

    # Scraping
    firecrawl_api_key: str = Field(default="")
    proxy_pool_url: str = Field(default="")
    user_agent_rotation: bool = Field(default=True)
    playwright_headless: bool = Field(default=True)

    # Observability
    sentry_dsn: str = Field(default="")
    otel_exporter_otlp_endpoint: str = Field(default="")

    model_config = {"env_file": ".env", "case_sensitive": False, "extra": "ignore"}


settings = Settings()
