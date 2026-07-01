from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.clients.doubao import DoubaoTtsClient, DoubaoTtsConfig
from app.clients.fake import FakeLoveSongClient, FakeTosStorage, FakeTtsClient
from app.clients.love_song import HttpLoveSongClient, LoveSongHttpConfig
from app.clients.tos_storage import TosStorage, TosStorageConfig
from app.core.config import Settings


class ConfigurationError(RuntimeError):
    pass


def load_required_json_config(settings: Settings, path_value: str, label: str) -> dict[str, Any]:
    path = settings.resolve_backend_path(path_value)
    if not path.exists():
        raise ConfigurationError(f"{label} config file not found: {path}")
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except json.JSONDecodeError as exc:
        raise ConfigurationError(f"{label} config file is invalid JSON: {path}") from exc
    if not isinstance(data, dict):
        raise ConfigurationError(f"{label} config file must contain a JSON object: {path}")
    return data


def build_tts_client(settings: Settings):
    if settings.tts_mode == "fake":
        return FakeTtsClient()
    if settings.tts_mode == "doubao":
        data = load_required_json_config(settings, settings.doubao_config_path, "doubao")
        try:
            return DoubaoTtsClient(DoubaoTtsConfig.from_mapping(data))
        except ValueError as exc:
            raise ConfigurationError(str(exc)) from exc
    raise ConfigurationError(f"unsupported tts mode: {settings.tts_mode}")


def build_audio_storage(settings: Settings):
    if settings.storage_mode == "fake":
        return FakeTosStorage()
    if settings.storage_mode == "tos":
        data = load_required_json_config(settings, settings.tos_config_path, "tos")
        try:
            return TosStorage(TosStorageConfig.from_mapping(data))
        except ValueError as exc:
            raise ConfigurationError(str(exc)) from exc
    raise ConfigurationError(f"unsupported storage mode: {settings.storage_mode}")


def build_love_song_client(settings: Settings):
    if settings.love_song_mode == "fake":
        return FakeLoveSongClient()
    if settings.love_song_mode == "http":
        data = load_required_json_config(settings, settings.love_song_config_path, "love-song")
        try:
            return HttpLoveSongClient.from_config(LoveSongHttpConfig.from_mapping(data))
        except ValueError as exc:
            raise ConfigurationError(str(exc)) from exc
    raise ConfigurationError(f"unsupported love-song mode: {settings.love_song_mode}")


def ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
