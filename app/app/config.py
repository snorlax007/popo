from __future__ import annotations

import secrets
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Popo Cloud"
    app_tagline: str = "The backend that gives your desk a soul."
    secret_key: str = secrets.token_urlsafe(32)
    admin_email: str = "admin@popo.local"
    admin_password: str = "changeme123"

    database_url: str = "sqlite+aiosqlite:///./popo.db"
    redis_url: str = "redis://localhost:6379/0"
    weather_cache_ttl: int = 600  # seconds

    anthropic_api_key: str = ""
    owm_api_key: str = ""

    s3_bucket: str = "popo-firmware"
    s3_endpoint_url: str = ""
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    ota_url_expiry: int = 3600

    mqtt_host: str = "localhost"
    mqtt_port: int = 1883
    mqtt_user: str = ""
    mqtt_pass: str = ""

    sentry_dsn: str = ""

    jwt_algorithm: str = "HS256"
    device_token_expire_days: int = 30
    user_token_expire_days: int = 7
    session_expire_hours: int = 24

    # Per-device daily LLM cap
    device_llm_daily_cap: int = 500

    class Config:
        env_file = ".env"


settings = Settings()
