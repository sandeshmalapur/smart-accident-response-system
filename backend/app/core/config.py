"""
Application configuration.

All secrets/config come from environment variables (.env in local dev),
per PROJECT_CONSTITUTION.md non-negotiable #5: never hardcode secrets.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/smart_accident_db"
    database_url_sync: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/smart_accident_db"

    # JWT
    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440

    # MQTT
    mqtt_broker_host: str = "localhost"
    mqtt_broker_port: int = 1883
    mqtt_client_id: str = "safe-backend"
    mqtt_keepalive: int = 60

    # App
    app_env: str = "local"
    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
