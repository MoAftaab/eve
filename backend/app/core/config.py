from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "EVE Healthcare API"
    environment: str = "development"
    database_url: str = "sqlite:///./eve_healthcare.db"
    jwt_secret: str = "change-me-in-production"
    jwt_expire_minutes: int = 60
    cors_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173"
    )
    redis_url: str = "redis://localhost:6379/0"
    webhook_secret: str = "local-webhook-secret"
    default_currency: str = "INR"
    rate_limit_per_minute: int = 120

    model_config = SettingsConfigDict(env_file=".env", env_prefix="EVE_", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
