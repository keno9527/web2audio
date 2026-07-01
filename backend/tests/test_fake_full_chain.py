from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import func, select


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.audio_jobs import process_article_audio  # noqa: E402
from app.clients.fake import FakeLoveSongClient, FakeTosStorage, FakeTtsClient  # noqa: E402
from app.clients.tts import AudioSynthesisResult  # noqa: E402
from app.main import (  # noqa: E402
    AUDIO_FAILED,
    AUDIO_READY,
    PLAYER_FAILED,
    PLAYER_READY,
    TEXT_FAILED,
    TEXT_READY,
    ArticleAudioItem,
)
from app.player_sync_jobs import process_player_sync  # noqa: E402
from app.self_test import fake_article_payload, run_fake_full_chain  # noqa: E402
from app.text_jobs import process_article_text  # noqa: E402


TOKEN = "test-token"
PLAYLIST_ID = "pl_today_reading"


def auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {TOKEN}"}


class FailingTtsClient:
    def synthesize(self, text: str, language: str | None = None) -> AudioSynthesisResult:
        raise RuntimeError("tts unavailable")


class FailingLoveSongClient:
    def register_tos_asset(self, request):
        raise RuntimeError("love-song unavailable")

    def append_track_to_playlist(self, playlist_id: str, track_id: str):
        raise AssertionError("append should not run when registration fails")


def test_fake_full_chain_reaches_playable_article_state(mysql_app_factory) -> None:
    app = mysql_app_factory(TOKEN)
    client = TestClient(app)

    result = run_fake_full_chain(
        app,
        auth_token=TOKEN,
        playlist_id=PLAYLIST_ID,
        payload=fake_article_payload(),
    )
    detail = client.get(f"/api/articles/{result.article_id}", headers=auth_headers())
    detail_body = detail.json()

    assert result.playable is True
    assert result.status == "playable"
    assert result.track_id is not None
    assert result.asset_id is not None
    assert detail.status_code == 200
    assert detail_body["status"] == "playable"
    assert detail_body["text_status"] == "ready"
    assert detail_body["audio_status"] == "ready"
    assert detail_body["player_sync_status"] == "ready"
    assert detail_body["love_song_track_id"] == result.track_id
    assert detail_body["love_song_asset_id"] == result.asset_id
    assert detail_body["love_song_playlist_id"] == PLAYLIST_ID
    assert result.love_song_client.playlist_tracks[PLAYLIST_ID] == [result.track_id]
    assert result.audio_storage_key in result.storage.objects


def test_duplicate_submission_after_playable_keeps_single_article_and_playlist_track(
    mysql_app_factory,
) -> None:
    app = mysql_app_factory(TOKEN)
    client = TestClient(app)
    payload = fake_article_payload()

    result = run_fake_full_chain(
        app,
        auth_token=TOKEN,
        playlist_id=PLAYLIST_ID,
        payload=payload,
    )
    duplicate = client.post("/api/articles", json=payload, headers=auth_headers())
    duplicate_body = duplicate.json()

    with app.state.session_factory() as session:
        article_count = session.scalar(
            select(func.count())
            .select_from(ArticleAudioItem)
            .where(
                ArticleAudioItem.owner_user_id == app.state.settings.owner_user_id,
                ArticleAudioItem.source_url == payload["source_url"],
            )
        )
        resync = process_player_sync(
            session,
            result.article_id,
            love_song_client=result.love_song_client,
            playlist_id=PLAYLIST_ID,
        )
        article = session.scalar(
            select(ArticleAudioItem).where(ArticleAudioItem.article_id == result.article_id)
        )

    assert duplicate.status_code == 200
    assert duplicate_body["created"] is False
    assert duplicate_body["article_id"] == result.article_id
    assert article_count == 1
    assert resync.synced is True
    assert resync.track_id == result.track_id
    assert resync.asset_id == result.asset_id
    assert article is not None
    assert article.player_sync_status == PLAYER_READY
    assert result.love_song_client.playlist_tracks[PLAYLIST_ID] == [result.track_id]


def test_invalid_article_text_does_not_generate_audio_or_player_side_effects(
    mysql_app_factory,
) -> None:
    app = mysql_app_factory(TOKEN)
    client = TestClient(app)
    payload = fake_article_payload()
    storage = FakeTosStorage()
    love_song_client = FakeLoveSongClient()
    created = client.post("/api/articles", json=payload, headers=auth_headers())
    article_id = created.json()["article_id"]

    with app.state.session_factory() as session:
        text_result = process_article_text(session, article_id, min_chars=1000)
        audio_result = process_article_audio(
            session,
            article_id,
            tts_client=FakeTtsClient(),
            storage=storage,
        )
        player_result = process_player_sync(
            session,
            article_id,
            love_song_client=love_song_client,
            playlist_id=PLAYLIST_ID,
        )
        article = session.scalar(
            select(ArticleAudioItem).where(ArticleAudioItem.article_id == article_id)
        )

    assert text_result.processed is False
    assert text_result.error_code == "text_too_short"
    assert audio_result.generated is False
    assert audio_result.error_code == "text_not_ready"
    assert player_result.synced is False
    assert player_result.error_code == "audio_not_ready"
    assert article is not None
    assert article.text_status == TEXT_FAILED
    assert article.audio_status == AUDIO_FAILED
    assert article.player_sync_status == PLAYER_FAILED
    assert article.audio_storage_key is None
    assert article.love_song_track_id is None
    assert article.love_song_asset_id is None
    assert article.love_song_playlist_id is None
    assert storage.objects == {}
    assert love_song_client.assets == {}
    assert love_song_client.playlist_tracks == {}


def test_tts_failure_does_not_create_playable_article_or_love_song_side_effects(
    mysql_app_factory,
) -> None:
    app = mysql_app_factory(TOKEN)
    client = TestClient(app)
    payload = fake_article_payload()
    storage = FakeTosStorage()
    love_song_client = FakeLoveSongClient()
    created = client.post("/api/articles", json=payload, headers=auth_headers())
    article_id = created.json()["article_id"]

    with app.state.session_factory() as session:
        text_result = process_article_text(session, article_id, max_segment_chars=14)
        audio_result = process_article_audio(
            session,
            article_id,
            tts_client=FailingTtsClient(),
            storage=storage,
        )
        player_result = process_player_sync(
            session,
            article_id,
            love_song_client=love_song_client,
            playlist_id=PLAYLIST_ID,
        )
        article = session.scalar(
            select(ArticleAudioItem).where(ArticleAudioItem.article_id == article_id)
        )

    detail = client.get(f"/api/articles/{article_id}", headers=auth_headers()).json()

    assert text_result.processed is True
    assert audio_result.generated is False
    assert audio_result.error_code == "tts_generation_failed"
    assert player_result.synced is False
    assert player_result.error_code == "audio_not_ready"
    assert article is not None
    assert article.text_status == TEXT_READY
    assert article.audio_status == AUDIO_FAILED
    assert article.player_sync_status == PLAYER_FAILED
    assert article.audio_storage_key is None
    assert article.love_song_track_id is None
    assert storage.objects == {}
    assert love_song_client.assets == {}
    assert detail["status"] == "failed"
    assert detail["audio_status"] == "failed"
    assert detail["player_sync_status"] == "failed"


def test_love_song_sync_failure_retains_audio_and_can_recover(
    mysql_app_factory,
) -> None:
    app = mysql_app_factory(TOKEN)
    client = TestClient(app)
    payload = fake_article_payload()
    storage = FakeTosStorage()
    created = client.post("/api/articles", json=payload, headers=auth_headers())
    article_id = created.json()["article_id"]
    recovered_love_song_client = FakeLoveSongClient()

    with app.state.session_factory() as session:
        process_article_text(session, article_id, max_segment_chars=14)
        audio_result = process_article_audio(
            session,
            article_id,
            tts_client=FakeTtsClient(),
            storage=storage,
        )
        failed_sync = process_player_sync(
            session,
            article_id,
            love_song_client=FailingLoveSongClient(),
            playlist_id=PLAYLIST_ID,
        )
        failed_article = session.scalar(
            select(ArticleAudioItem).where(ArticleAudioItem.article_id == article_id)
        )
        retained_storage_key = failed_article.audio_storage_key if failed_article else None
        recovered_sync = process_player_sync(
            session,
            article_id,
            love_song_client=recovered_love_song_client,
            playlist_id=PLAYLIST_ID,
        )
        recovered_article = session.scalar(
            select(ArticleAudioItem).where(ArticleAudioItem.article_id == article_id)
        )

    detail = client.get(f"/api/articles/{article_id}", headers=auth_headers()).json()

    assert audio_result.generated is True
    assert audio_result.storage_key in storage.objects
    assert failed_sync.synced is False
    assert failed_sync.error_code == "love_song_sync_failed"
    assert retained_storage_key == audio_result.storage_key
    assert recovered_sync.synced is True
    assert recovered_sync.track_id is not None
    assert recovered_article is not None
    assert recovered_article.audio_status == AUDIO_READY
    assert recovered_article.player_sync_status == PLAYER_READY
    assert recovered_article.audio_storage_key == audio_result.storage_key
    assert recovered_article.love_song_track_id == recovered_sync.track_id
    assert recovered_love_song_client.playlist_tracks[PLAYLIST_ID] == [recovered_sync.track_id]
    assert detail["status"] == "playable"
    assert detail["love_song_track_id"] == recovered_sync.track_id
