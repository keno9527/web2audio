from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_ROOT = Path(__file__).resolve().parents[2]
CONF_DIR = BACKEND_ROOT / "conf"

DEFAULT_DATABASE_URL = (
    "mysql+pymysql://web2audio:web2audio@127.0.0.1:3306/web2audio?charset=utf8mb4"
)
DEFAULT_AUTH_TOKEN = "dev-token"
DEFAULT_OWNER_USER_ID = "default"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=CONF_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "web2audio"
    env: str = "development"
    database_url: str = DEFAULT_DATABASE_URL
    database_config_path: str = "conf/db.local.json"
    database_profile: str = ""
    auth_token: str = DEFAULT_AUTH_TOKEN
    owner_user_id: str = DEFAULT_OWNER_USER_ID

    tts_mode: Literal["fake", "doubao"] = "fake"
    storage_mode: Literal["fake", "tos"] = "fake"
    love_song_mode: Literal["fake", "http"] = "fake"

    doubao_config_path: str = "conf/doubao.local.json"
    tos_config_path: str = "conf/tos.local.json"
    love_song_config_path: str = "conf/love_song.local.json"

    def resolve_backend_path(self, value: str) -> Path:
        path = Path(value)
        if path.is_absolute():
            return path
        return BACKEND_ROOT / path

    def resolve_database_url(self) -> str:
        if self.database_url and self.database_url != DEFAULT_DATABASE_URL:
            return self._ensure_mysql_database_url(self.database_url)

        path = self.resolve_backend_path(self.database_config_path)
        if not path.exists():
            return self._ensure_mysql_database_url(self.database_url or DEFAULT_DATABASE_URL)

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"db config file is invalid JSON: {path}") from exc
        if not isinstance(data, dict):
            raise ValueError(f"db config file must contain a JSON object: {path}")

        active_profile = self.database_profile or str(data.get("active") or "")
        profiles = data.get("profiles")
        if not active_profile or not isinstance(profiles, dict):
            raise ValueError("db config missing required fields: active, profiles")

        profile = profiles.get(active_profile)
        if not isinstance(profile, dict):
            raise ValueError(f"db config profile not found: {active_profile}")

        driver = str(profile.get("driver") or "")
        if driver and driver != "mysql":
            raise ValueError(f"db config profile must use mysql driver: {active_profile}")

        database_url = str(profile.get("database_url") or "")
        if not database_url:
            raise ValueError(f"db config profile missing database_url: {active_profile}")
        return self._ensure_mysql_database_url(database_url)

    def _ensure_mysql_database_url(self, database_url: str) -> str:
        if not database_url.startswith("mysql+pymysql://"):
            raise ValueError(
                "database_url must use mysql+pymysql://; local SQLite is no longer supported"
            )
        return database_url


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
