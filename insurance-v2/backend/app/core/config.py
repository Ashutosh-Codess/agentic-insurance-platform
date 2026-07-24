"""
Application settings, loaded from environment variables (.env locally,
real env vars in Docker). Keeping every tunable here means nothing is
hardcoded elsewhere in the codebase.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Insurance Platform API"
    API_PREFIX: str = "/api/v1"

    DATABASE_URL: str = "postgresql+psycopg2://insurance:insurance@postgres:5432/insurance"

    JWT_SECRET_KEY: str = "change-me-in-prod"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    CUSTOMER_PORTAL_ORIGIN: str = "http://localhost:5173"
    AGENT_PORTAL_ORIGIN: str = "http://localhost:5174"

    UPLOAD_DIR: str = "uploads"
    REPORTS_DIR: str = "reports"

    # The two accounts that exist without any app usage.
    SEED_ADMIN_EMAIL: str = "admin@platform.internal"
    SEED_ADMIN_PASSWORD: str = "ChangeMe!Admin123"
    SEED_AGENT_EMAIL: str = "agent@platform.internal"
    SEED_AGENT_PASSWORD: str = "ChangeMe!Agent123"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
