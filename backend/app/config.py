from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    database_url: str = f"sqlite:///{BACKEND_DIR / 'data' / 'finance_bro.db'}"
    frontend_origin: str = "http://localhost:5173"
    pluggy_client_id: str = ""
    pluggy_client_secret: str = ""
    pluggy_api_url: str = "https://api.pluggy.ai"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env", env_file_encoding="utf-8", extra="ignore"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
