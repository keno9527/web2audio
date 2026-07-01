from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.audio_jobs import process_article_audio  # noqa: E402
from app.clients.tos_storage import TosStorage  # noqa: E402
from app.core.config import Settings  # noqa: E402
from app.main import (  # noqa: E402
    AUDIO_READY,
    PLAYER_READY,
    TEXT_READY,
    ArticleAudioItem,
    ArticleTtsSegment,
)
from app.player_sync_jobs import process_player_sync  # noqa: E402
from app.runtime import build_audio_storage, build_love_song_client, build_tts_client  # noqa: E402
from app.text_jobs import process_article_text  # noqa: E402


TOKEN = "live-e2e-token"
DEFAULT_PLAYLIST_ID = "demo_playlist_focus"


def auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {TOKEN}"}


def live_article_payload(case_id: str) -> dict[str, str]:
    run_id = uuid4().hex[:12]
    return {
        "source_url": f"https://example.com/web2audio/live-e2e/{case_id}/{run_id}",
        "title": f"web2audio {case_id} 真实联调文章",
        "text_content": (
            "这是 web2audio 端到端真实联调文章。"
            "内容用于验证豆包语音合成、火山云 TOS 上传和播放器同步。"
            "文本保持较短，以控制真实外部调用成本。"
        ),
        "site_name": "web2audio E2E",
        "author": "web2audio",
        "published_at": "2026-06-29T10:00:00Z",
        "cover_url": "https://example.com/web2audio-cover.png",
        "language_hint": "zh-CN",
    }


def live_settings() -> Settings:
    return Settings(tts_mode="doubao", storage_mode="tos", love_song_mode="http")


def assert_tos_objects_exist(storage: TosStorage, object_keys: list[str]) -> None:
    client = storage._tos_client()
    for object_key in object_keys:
        assert client.does_object_exist(storage.config.bucket, object_key) is True
        metadata = client.head_object(storage.config.bucket, object_key)
        assert metadata.status_code == 200
        assert metadata.content_length > 1024


def cleanup_tos_objects(storage: TosStorage, object_keys: list[str]) -> None:
    if os.getenv("W2A_E2E_KEEP_OBJECTS") == "1":
        return
    client = storage._tos_client()
    for object_key in object_keys:
        try:
            if client.does_object_exist(storage.config.bucket, object_key):
                client.delete_object(storage.config.bucket, object_key)
        except Exception:
            pass


def load_love_song_config(settings: Settings) -> dict[str, object]:
    path = settings.resolve_backend_path(settings.love_song_config_path)
    return json.loads(path.read_text(encoding="utf-8"))


def love_song_endpoint(settings: Settings) -> tuple[str, float]:
    config = load_love_song_config(settings)
    base_url = str(config["base_url"]).rstrip("/")
    timeout = float(config.get("timeout") or 10)
    return base_url, timeout


def love_song_get_playlist(settings: Settings, playlist_id: str) -> dict[str, object]:
    base_url, timeout = love_song_endpoint(settings)
    response = httpx.get(f"{base_url}/api/playlists/{playlist_id}", timeout=timeout)
    response.raise_for_status()
    return response.json()


def love_song_post(settings: Settings, path: str, payload: dict[str, object]) -> dict[str, object]:
    base_url, timeout = love_song_endpoint(settings)
    response = httpx.post(f"{base_url}{path}", json=payload, timeout=timeout)
    response.raise_for_status()
    return response.json()


def love_song_patch(settings: Settings, path: str, payload: dict[str, object]) -> dict[str, object]:
    base_url, timeout = love_song_endpoint(settings)
    response = httpx.patch(f"{base_url}{path}", json=payload, timeout=timeout)
    response.raise_for_status()
    return response.json()


def fetch_playlist_track(
    settings: Settings,
    playlist_id: str,
    track_id: str,
) -> dict[str, object]:
    tracks = love_song_get_playlist(settings, playlist_id)["tracks"]
    matches = [track for track in tracks if track["track_id"] == track_id]
    assert len(matches) == 1
    return matches[0]


def cleanup_love_song_playlist_track(
    settings: Settings,
    playlist_id: str,
    track_id: str | None,
) -> None:
    if not track_id or os.getenv("W2A_E2E_KEEP_LOVE_SONG_TRACK") == "1":
        return
    config = load_love_song_config(settings)
    base_url = str(config["base_url"]).rstrip("/")
    timeout = float(config.get("timeout") or 10)
    try:
        httpx.delete(f"{base_url}/api/playlists/{playlist_id}/tracks/{track_id}", timeout=timeout)
    except Exception:
        pass


def submit_live_article(mysql_app_factory, payload: dict[str, str]):
    app = mysql_app_factory(TOKEN, owner_user_id=f"live_e2e_{uuid4().hex}")
    client = TestClient(app)
    created = client.post("/api/articles", json=payload, headers=auth_headers())
    assert created.status_code == 201
    return app, client, created.json()["article_id"]


def test_w2a_e2e_008_real_doubao_tts_and_tos_audio_job(mysql_app_factory) -> None:
    if os.getenv("W2A_RUN_REAL_AUDIO_JOB") != "1":
        pytest.skip("set W2A_RUN_REAL_AUDIO_JOB=1 to run W2A-E2E-008 live audio job")

    settings = live_settings()
    tts_client = build_tts_client(settings)
    storage = build_audio_storage(settings)
    assert isinstance(storage, TosStorage)
    app, client, article_id = submit_live_article(
        mysql_app_factory,
        live_article_payload("W2A-E2E-008"),
    )
    object_keys: list[str] = []

    try:
        with app.state.session_factory() as session:
            text_result = process_article_text(session, article_id)
            audio_result = process_article_audio(
                session,
                article_id,
                tts_client=tts_client,
                storage=storage,
            )
            article = session.scalar(
                select(ArticleAudioItem).where(ArticleAudioItem.article_id == article_id)
            )
            segments = session.scalars(
                select(ArticleTtsSegment)
                .where(ArticleTtsSegment.article_id == article_id)
                .order_by(ArticleTtsSegment.segment_index)
            ).all()

        assert text_result.processed is True
        assert audio_result.generated is True
        assert audio_result.error_code is None
        assert audio_result.segment_count == len(segments)
        assert article is not None
        assert article.text_status == TEXT_READY
        assert article.audio_status == AUDIO_READY
        assert article.audio_storage_key
        assert article.duration_seconds and article.duration_seconds >= 1
        assert segments
        assert all(segment.audio_storage_key for segment in segments)

        object_keys = [segment.audio_storage_key for segment in segments if segment.audio_storage_key]
        object_keys.append(article.audio_storage_key)
        assert_tos_objects_exist(storage, object_keys)

        detail = client.get(f"/api/articles/{article_id}", headers=auth_headers())
        assert detail.status_code == 200
        assert detail.json()["audio_status"] == "ready"
    finally:
        cleanup_tos_objects(storage, object_keys)


def test_w2a_e2e_010_real_doubao_tos_and_love_song_full_chain(mysql_app_factory) -> None:
    if os.getenv("W2A_RUN_REAL_FULL_CHAIN") != "1":
        pytest.skip("set W2A_RUN_REAL_FULL_CHAIN=1 to run W2A-E2E-010 live full chain")

    settings = live_settings()
    tts_client = build_tts_client(settings)
    storage = build_audio_storage(settings)
    love_song_client = build_love_song_client(settings)
    assert isinstance(storage, TosStorage)
    playlist_id = os.getenv("W2A_LOVE_SONG_PLAYLIST_ID", DEFAULT_PLAYLIST_ID)
    payload = live_article_payload("W2A-E2E-010")
    app, client, article_id = submit_live_article(mysql_app_factory, payload)
    object_keys: list[str] = []
    track_id: str | None = None

    try:
        with app.state.session_factory() as session:
            text_result = process_article_text(session, article_id)
            audio_result = process_article_audio(
                session,
                article_id,
                tts_client=tts_client,
                storage=storage,
            )
            sync_result = process_player_sync(
                session,
                article_id,
                love_song_client=love_song_client,
                playlist_id=playlist_id,
            )
            article = session.scalar(
                select(ArticleAudioItem).where(ArticleAudioItem.article_id == article_id)
            )
            segments = session.scalars(
                select(ArticleTtsSegment)
                .where(ArticleTtsSegment.article_id == article_id)
                .order_by(ArticleTtsSegment.segment_index)
            ).all()

        assert text_result.processed is True
        assert audio_result.generated is True
        assert sync_result.synced is True
        track_id = sync_result.track_id
        assert track_id
        assert sync_result.asset_id
        assert article is not None
        assert article.text_status == TEXT_READY
        assert article.audio_status == AUDIO_READY
        assert article.player_sync_status == PLAYER_READY
        assert article.audio_storage_key
        assert article.love_song_track_id == sync_result.track_id
        assert article.love_song_asset_id == sync_result.asset_id
        assert article.love_song_playlist_id == playlist_id

        object_keys = [segment.audio_storage_key for segment in segments if segment.audio_storage_key]
        object_keys.append(article.audio_storage_key)
        assert_tos_objects_exist(storage, object_keys)

        detail = client.get(f"/api/articles/{article_id}", headers=auth_headers())
        assert detail.status_code == 200
        detail_body = detail.json()
        assert detail_body["status"] == "playable"
        assert detail_body["text_status"] == "ready"
        assert detail_body["audio_status"] == "ready"
        assert detail_body["player_sync_status"] == "ready"

        playlist_track = fetch_playlist_track(settings, playlist_id, track_id)
        assert playlist_track["title"] == payload["title"]
        assert playlist_track["content_type"] == "article_audio"
        assert playlist_track["subtitle"] == payload["site_name"]
        assert playlist_track["duration_seconds"] == article.duration_seconds
    finally:
        cleanup_love_song_playlist_track(settings, playlist_id, track_id)
        cleanup_tos_objects(storage, object_keys)


def require_real_full_chain() -> None:
    if os.getenv("W2A_RUN_REAL_FULL_CHAIN") != "1":
        pytest.skip("set W2A_RUN_REAL_FULL_CHAIN=1 to run live iOS-facing playback E2E")


def run_full_chain_to_playable(
    mysql_app_factory,
    *,
    settings: Settings,
    case_id: str,
    playlist_id: str,
    tts_client,
    storage: TosStorage,
    love_song_client,
) -> dict[str, object]:
    payload = live_article_payload(case_id)
    app, _, article_id = submit_live_article(mysql_app_factory, payload)

    with app.state.session_factory() as session:
        text_result = process_article_text(session, article_id)
        audio_result = process_article_audio(
            session,
            article_id,
            tts_client=tts_client,
            storage=storage,
        )
        sync_result = process_player_sync(
            session,
            article_id,
            love_song_client=love_song_client,
            playlist_id=playlist_id,
        )
        article = session.scalar(
            select(ArticleAudioItem).where(ArticleAudioItem.article_id == article_id)
        )
        segments = session.scalars(
            select(ArticleTtsSegment)
            .where(ArticleTtsSegment.article_id == article_id)
            .order_by(ArticleTtsSegment.segment_index)
        ).all()

        assert text_result.processed is True
        assert audio_result.generated is True
        assert sync_result.synced is True
        assert article is not None
        assert article.player_sync_status == PLAYER_READY
        assert sync_result.track_id and sync_result.asset_id

        object_keys = [
            segment.audio_storage_key for segment in segments if segment.audio_storage_key
        ]
        object_keys.append(article.audio_storage_key)
        return {
            "article_id": article_id,
            "track_id": sync_result.track_id,
            "asset_id": sync_result.asset_id,
            "duration_seconds": article.duration_seconds,
            "audio_storage_key": article.audio_storage_key,
            "object_keys": object_keys,
            "payload": payload,
        }


def test_w2a_e2e_011_ios_today_reading_playable_via_love_song_api(mysql_app_factory) -> None:
    require_real_full_chain()

    settings = live_settings()
    tts_client = build_tts_client(settings)
    storage = build_audio_storage(settings)
    love_song_client = build_love_song_client(settings)
    assert isinstance(storage, TosStorage)
    playlist_id = os.getenv("W2A_LOVE_SONG_PLAYLIST_ID", DEFAULT_PLAYLIST_ID)
    chain: dict[str, object] = {}

    try:
        chain = run_full_chain_to_playable(
            mysql_app_factory,
            settings=settings,
            case_id="W2A-E2E-011",
            playlist_id=playlist_id,
            tts_client=tts_client,
            storage=storage,
            love_song_client=love_song_client,
        )
        track_id = str(chain["track_id"])

        playlist_track = fetch_playlist_track(settings, playlist_id, track_id)
        assert playlist_track["title"] == chain["payload"]["title"]

        session = love_song_post(
            settings,
            "/api/playback-sessions",
            {"playlist_id": playlist_id, "start_track_id": track_id, "play_mode": "sequence"},
        )
        assert session["current_track_id"] == track_id
        assert session["current_asset_id"] == chain["asset_id"]
        assert track_id in session["ordered_track_ids"]

        playback_url = love_song_post(
            settings,
            "/api/playback-url",
            {"track_id": track_id, "session_id": session["session_id"]},
        )
        assert playback_url["track_id"] == track_id
        assert playback_url["asset_id"] == chain["asset_id"]
        assert playback_url["source_type"] == "tos"
        assert playback_url["mime_type"] == "audio/mpeg"
        assert playback_url["url"] == chain["audio_storage_key"]
    finally:
        cleanup_love_song_playlist_track(settings, playlist_id, chain.get("track_id"))
        cleanup_tos_objects(storage, list(chain.get("object_keys", [])))


def test_w2a_e2e_012_ios_article_semantics_via_love_song_api(mysql_app_factory) -> None:
    require_real_full_chain()

    settings = live_settings()
    tts_client = build_tts_client(settings)
    storage = build_audio_storage(settings)
    love_song_client = build_love_song_client(settings)
    assert isinstance(storage, TosStorage)
    playlist_id = os.getenv("W2A_LOVE_SONG_PLAYLIST_ID", DEFAULT_PLAYLIST_ID)
    chain: dict[str, object] = {}

    try:
        chain = run_full_chain_to_playable(
            mysql_app_factory,
            settings=settings,
            case_id="W2A-E2E-012",
            playlist_id=playlist_id,
            tts_client=tts_client,
            storage=storage,
            love_song_client=love_song_client,
        )
        track_id = str(chain["track_id"])
        payload = chain["payload"]

        playlist_track = fetch_playlist_track(settings, playlist_id, track_id)
        assert playlist_track["content_type"] == "article_audio"
        assert playlist_track["title"] == payload["title"]
        assert playlist_track["subtitle"] == payload["site_name"]
        assert playlist_track["artist"] is None
        assert playlist_track["album"] is None
        assert playlist_track["duration_seconds"] == chain["duration_seconds"]
    finally:
        cleanup_love_song_playlist_track(settings, playlist_id, chain.get("track_id"))
        cleanup_tos_objects(storage, list(chain.get("object_keys", [])))


def test_w2a_e2e_013_ios_sequential_playback_and_history_via_love_song_api(
    mysql_app_factory,
) -> None:
    require_real_full_chain()

    settings = live_settings()
    tts_client = build_tts_client(settings)
    storage = build_audio_storage(settings)
    love_song_client = build_love_song_client(settings)
    assert isinstance(storage, TosStorage)
    playlist_id = os.getenv("W2A_LOVE_SONG_PLAYLIST_ID", DEFAULT_PLAYLIST_ID)
    first: dict[str, object] = {}
    second: dict[str, object] = {}

    try:
        first = run_full_chain_to_playable(
            mysql_app_factory,
            settings=settings,
            case_id="W2A-E2E-013-A",
            playlist_id=playlist_id,
            tts_client=tts_client,
            storage=storage,
            love_song_client=love_song_client,
        )
        second = run_full_chain_to_playable(
            mysql_app_factory,
            settings=settings,
            case_id="W2A-E2E-013-B",
            playlist_id=playlist_id,
            tts_client=tts_client,
            storage=storage,
            love_song_client=love_song_client,
        )
        first_track = str(first["track_id"])
        second_track = str(second["track_id"])

        playlist = love_song_get_playlist(settings, playlist_id)
        positions = {
            track["track_id"]: track["position"]
            for track in playlist["tracks"]
            if track["track_id"] in {first_track, second_track}
        }
        assert positions[second_track] == positions[first_track] + 1

        session = love_song_post(
            settings,
            "/api/playback-sessions",
            {"playlist_id": playlist_id, "start_track_id": first_track, "play_mode": "sequence"},
        )
        ordered = session["ordered_track_ids"]
        assert ordered.index(second_track) == ordered.index(first_track) + 1

        first_url = love_song_post(
            settings,
            "/api/playback-url",
            {"track_id": first_track, "session_id": session["session_id"]},
        )
        assert first_url["url"] == first["audio_storage_key"]

        started = love_song_post(
            settings,
            "/api/play-history",
            {
                "track_id": first_track,
                "playlist_id": playlist_id,
                "session_id": session["session_id"],
                "source_asset_id": first["asset_id"],
                "event": "started",
                "position_seconds": 0,
            },
        )
        assert started["track_id"] == first_track
        assert started["event"] == "started"

        advanced = love_song_patch(
            settings,
            f"/api/playback-sessions/{session['session_id']}",
            {"current_track_id": second_track, "position_seconds": 0, "is_playing": True},
        )
        assert advanced["current_track_id"] == second_track
        assert advanced["current_asset_id"] == second["asset_id"]

        second_url = love_song_post(
            settings,
            "/api/playback-url",
            {"track_id": second_track, "session_id": session["session_id"]},
        )
        assert second_url["url"] == second["audio_storage_key"]

        completed = love_song_post(
            settings,
            "/api/play-history",
            {
                "track_id": second_track,
                "playlist_id": playlist_id,
                "session_id": session["session_id"],
                "source_asset_id": second["asset_id"],
                "event": "started",
                "position_seconds": 0,
            },
        )
        assert completed["track_id"] == second_track
    finally:
        cleanup_love_song_playlist_track(settings, playlist_id, second.get("track_id"))
        cleanup_love_song_playlist_track(settings, playlist_id, first.get("track_id"))
        cleanup_tos_objects(storage, list(first.get("object_keys", [])))
        cleanup_tos_objects(storage, list(second.get("object_keys", [])))
