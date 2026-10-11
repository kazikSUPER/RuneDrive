import os

from pydantic_settings import BaseSettings, SettingsConfigDict


def get_env_file() -> str:
    """Визначає цільовий файл оточення залежно від змінної APP_ENV / ENVIRONMENT."""
    env = os.getenv("APP_ENV", os.getenv("ENVIRONMENT", "sandbox")).lower()
    if env in ("production", "prod"):
        return ".env.production"
    if env in ("sandbox", "dev", "development"):
        return ".env.sandbox"
    return ".env"


class Settings(BaseSettings):
    ENVIRONMENT: str = "sandbox"
    DEBUG: bool = True

    PROJECT_NAME: str = "RuneDrive API"
    VERSION: str = "0.1.0"
    DESCRIPTION: str = "Highload Marketplace for Cybernetic and Magical Modifications"
    API_V1_STR: str = "/api/v1"

    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "runedrive"

    DATABASE_URL: str | None = None

    @property
    def async_database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    JWT_SECRET_KEY: str = "rune_super_secret_cyber_jwt_key_2026_master"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    model_config = SettingsConfigDict(
        env_file=get_env_file(),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
