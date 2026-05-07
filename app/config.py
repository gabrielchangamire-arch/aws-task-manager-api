from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    log_level: str = "INFO"

    database_url: str = "sqlite:///./tasks.db"

    s3_enabled: bool = False
    aws_region: str = "us-west-2"
    s3_bucket_name: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
