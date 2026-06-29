from __future__ import annotations

import sys
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.clients.doubao import DoubaoTtsClient  # noqa: E402
from app.clients.fake import FakeLoveSongClient, FakeTosStorage, FakeTtsClient  # noqa: E402
from app.core.config import BACKEND_ROOT, DEFAULT_DATABASE_URL, Settings  # noqa: E402
from app.runtime import (  # noqa: E402
    ConfigurationError,
    build_audio_storage,
    build_love_song_client,
    build_tts_client,
)


def test_settings_defaults_to_fake_runtime_and_mysql_database(tmp_path: Path) -> None:
    settings = Settings(
        database_url=DEFAULT_DATABASE_URL,
        database_config_path=str(tmp_path / "missing-db.local.json"),
    )

    assert settings.database_url == DEFAULT_DATABASE_URL
    assert settings.resolve_database_url() == DEFAULT_DATABASE_URL
    assert settings.auth_token == "dev-token"
    assert settings.tts_mode == "fake"
    assert settings.storage_mode == "fake"
    assert settings.love_song_mode == "fake"
    assert settings.resolve_backend_path("conf/tos.local.json") == BACKEND_ROOT / "conf/tos.local.json"


def test_default_runtime_builds_fake_clients() -> None:
    settings = Settings()

    assert isinstance(build_tts_client(settings), FakeTtsClient)
    assert isinstance(build_audio_storage(settings), FakeTosStorage)
    assert isinstance(build_love_song_client(settings), FakeLoveSongClient)


def test_real_runtime_modes_fail_fast_when_config_file_is_missing(tmp_path: Path) -> None:
    settings = Settings(
        tts_mode="doubao",
        storage_mode="tos",
        love_song_mode="http",
        doubao_config_path=str(tmp_path / "missing-doubao.json"),
        tos_config_path=str(tmp_path / "missing-tos.json"),
        love_song_config_path=str(tmp_path / "missing-love-song.json"),
    )

    with pytest.raises(ConfigurationError, match="doubao config file"):
        build_tts_client(settings)

    with pytest.raises(ConfigurationError, match="tos config file"):
        build_audio_storage(settings)

    with pytest.raises(ConfigurationError, match="love-song config file"):
        build_love_song_client(settings)


def test_settings_resolves_database_url_from_active_profile(tmp_path: Path) -> None:
    db_config = tmp_path / "db.local.json"
    db_config.write_text(
        """
        {
          "active": "mysql",
          "profiles": {
            "mysql": {
              "driver": "mysql",
              "database_url": "mysql+pymysql://user:pass@127.0.0.1:3306/web2audio?charset=utf8mb4"
            }
          }
        }
        """,
        encoding="utf-8",
    )
    settings = Settings(
        database_url=DEFAULT_DATABASE_URL,
        database_config_path=str(db_config),
    )

    assert (
        settings.resolve_database_url()
        == "mysql+pymysql://user:pass@127.0.0.1:3306/web2audio?charset=utf8mb4"
    )


def test_settings_rejects_local_sqlite_database_url() -> None:
    settings = Settings(database_url="sqlite:///./web2audio.db")

    with pytest.raises(ValueError, match="local SQLite is no longer supported"):
        settings.resolve_database_url()


def test_real_tts_runtime_builds_doubao_websocket_client_from_config(tmp_path: Path) -> None:
    doubao_config = tmp_path / "doubao.local.json"
    doubao_config.write_text(
        """
        {
          "api_key": "test-key",
          "resource_id": "seed-tts-2.0",
          "speaker": "zh_female_test",
          "audio_format": "mp3",
          "sample_rate": 24000,
          "bit_rate": 128000
        }
        """,
        encoding="utf-8",
    )
    settings = Settings(
        tts_mode="doubao",
        doubao_config_path=str(doubao_config),
    )

    assert isinstance(build_tts_client(settings), DoubaoTtsClient)
