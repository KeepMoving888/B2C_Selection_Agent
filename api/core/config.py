# api/core/config.py
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "选品决策系统 API"
    app_version: str = "1.0.0"
    debug: bool = True
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 60 * 24

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
