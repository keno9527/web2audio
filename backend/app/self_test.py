from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.audio_jobs import FakeTosStorage, FakeTtsClient, process_article_audio
from app.love_song_contract import FakeLoveSongClient
from app.main import ArticleAudioItem
from app.player_sync_jobs import process_player_sync
from app.text_jobs import process_article_text


@dataclass(frozen=True)
class FakeFullChainResult:
    playable: bool
    status: str
    article_id: str
    track_id: str
    asset_id: str
    playlist_id: str
    audio_storage_key: str
    storage: FakeTosStorage
    love_song_client: FakeLoveSongClient


def fake_article_payload() -> Dict[str, str]:
    return {
        "source_url": "https://mp.weixin.qq.com/s/sVgTl03Hh3zaNFBh7X-ckQ",
        "title": "示例文章标题",
        "text_content": "第一段 内容足够长。\n\n第二段 内容也足够长。\n\n第三段结尾。",
        "site_name": "微信公众平台",
        "author": "作者",
        "published_at": "2026-06-27T08:00:00Z",
        "cover_url": "https://example.com/cover.jpg",
        "language_hint": "zh-CN",
    }


def run_fake_full_chain(
    app: FastAPI,
    *,
    auth_token: str,
    playlist_id: str,
    payload: Dict[str, Any],
) -> FakeFullChainResult:
    client = TestClient(app)
    headers = {"Authorization": f"Bearer {auth_token}"}
    created = client.post("/api/articles", json=payload, headers=headers)
    created.raise_for_status()
    article_id = created.json()["article_id"]

    storage = FakeTosStorage()
    love_song_client = FakeLoveSongClient()
    with app.state.session_factory() as session:
        process_article_text(session, article_id)
        process_article_audio(
            session,
            article_id,
            tts_client=FakeTtsClient(),
            storage=storage,
        )
        player_result = process_player_sync(
            session,
            article_id,
            love_song_client=love_song_client,
            playlist_id=playlist_id,
        )
        article = session.scalar(
            select(ArticleAudioItem).where(ArticleAudioItem.article_id == article_id)
        )
        if article is None or article.audio_storage_key is None:
            raise RuntimeError("fake full chain did not create article audio")

    detail = client.get(f"/api/articles/{article_id}", headers=headers)
    detail.raise_for_status()
    status = detail.json()["status"]

    return FakeFullChainResult(
        playable=status == "playable",
        status=status,
        article_id=article_id,
        track_id=player_result.track_id or "",
        asset_id=player_result.asset_id or "",
        playlist_id=playlist_id,
        audio_storage_key=article.audio_storage_key,
        storage=storage,
        love_song_client=love_song_client,
    )
