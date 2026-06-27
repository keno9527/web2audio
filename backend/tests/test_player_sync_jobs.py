from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.audio_jobs import FakeTosStorage, FakeTtsClient, process_article_audio  # noqa: E402
from app.love_song_contract import FakeLoveSongClient  # noqa: E402
from app.main import (  # noqa: E402
    AUDIO_READY,
    PLAYER_FAILED,
    PLAYER_READY,
    ArticleAudioItem,
    create_app,
)
from app.player_sync_jobs import process_player_sync  # noqa: E402
from app.text_jobs import process_article_text  # noqa: E402


TOKEN = "test-token"
ARTICLE_URL = "https://mp.weixin.qq.com/s/sVgTl03Hh3zaNFBh7X-ckQ"
PLAYLIST_ID = "pl_today_reading"


def auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {TOKEN}"}


def article_payload() -> dict[str, str]:
    return {
        "source_url": ARTICLE_URL,
        "title": "待同步文章",
        "text_content": "第一段 内容足够长。\n\n第二段 内容也足够长。\n\n第三段结尾。",
        "site_name": "微信公众平台",
        "language_hint": "zh-CN",
    }


def test_process_player_sync_registers_asset_and_appends_playlist_idempotently(
    tmp_path: Path,
) -> None:
    db_url = f"sqlite:///{tmp_path / 'web2audio-test.db'}"
    app = create_app(database_url=db_url, auth_token=TOKEN)
    client = TestClient(app)
    created = client.post("/api/articles", json=article_payload(), headers=auth_headers())
    article_id = created.json()["article_id"]
    love_song_client = FakeLoveSongClient()

    with app.state.session_factory() as session:
        process_article_text(session, article_id, max_segment_chars=14)
        process_article_audio(
            session,
            article_id,
            tts_client=FakeTtsClient(),
            storage=FakeTosStorage(),
        )
        first = process_player_sync(
            session,
            article_id,
            love_song_client=love_song_client,
            playlist_id=PLAYLIST_ID,
        )
        second = process_player_sync(
            session,
            article_id,
            love_song_client=love_song_client,
            playlist_id=PLAYLIST_ID,
        )
        article = session.scalar(
            select(ArticleAudioItem).where(ArticleAudioItem.article_id == article_id)
        )

    assert first.synced is True
    assert second.synced is True
    assert first.track_id == second.track_id
    assert first.asset_id == second.asset_id
    assert first.playlist_id == second.playlist_id == PLAYLIST_ID
    assert article is not None
    assert article.audio_status == AUDIO_READY
    assert article.player_sync_status == PLAYER_READY
    assert article.love_song_track_id == first.track_id
    assert article.love_song_asset_id == first.asset_id
    assert article.love_song_playlist_id == PLAYLIST_ID
    assert love_song_client.playlist_tracks[PLAYLIST_ID] == [first.track_id]


def test_process_player_sync_fails_when_audio_is_not_ready(tmp_path: Path) -> None:
    db_url = f"sqlite:///{tmp_path / 'web2audio-test.db'}"
    app = create_app(database_url=db_url, auth_token=TOKEN)
    client = TestClient(app)
    created = client.post("/api/articles", json=article_payload(), headers=auth_headers())
    article_id = created.json()["article_id"]

    with app.state.session_factory() as session:
        result = process_player_sync(
            session,
            article_id,
            love_song_client=FakeLoveSongClient(),
            playlist_id=PLAYLIST_ID,
        )
        article = session.scalar(
            select(ArticleAudioItem).where(ArticleAudioItem.article_id == article_id)
        )

    assert result.synced is False
    assert result.error_code == "audio_not_ready"
    assert article is not None
    assert article.player_sync_status == PLAYER_FAILED
