from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.audio_jobs import (  # noqa: E402
    FakeTosStorage,
    FakeTtsClient,
    process_article_audio,
)
from app.main import (  # noqa: E402
    AUDIO_READY,
    PLAYER_PENDING,
    TEXT_READY,
    ArticleAudioItem,
    ArticleTtsSegment,
    create_app,
)
from app.text_jobs import process_article_text  # noqa: E402


TOKEN = "test-token"
ARTICLE_URL = "https://mp.weixin.qq.com/s/sVgTl03Hh3zaNFBh7X-ckQ"


def auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {TOKEN}"}


def article_payload() -> dict[str, str]:
    return {
        "source_url": ARTICLE_URL,
        "title": "待生成音频文章",
        "text_content": "第一段 内容足够长。\n\n第二段 内容也足够长。\n\n第三段结尾。",
        "site_name": "微信公众平台",
        "language_hint": "zh-CN",
    }


def test_process_article_audio_generates_segment_and_final_tos_objects(tmp_path: Path) -> None:
    db_url = f"sqlite:///{tmp_path / 'web2audio-test.db'}"
    app = create_app(database_url=db_url, auth_token=TOKEN)
    client = TestClient(app)
    created = client.post("/api/articles", json=article_payload(), headers=auth_headers())
    article_id = created.json()["article_id"]
    storage = FakeTosStorage()
    tts_client = FakeTtsClient(duration_seconds_per_char=0.5)

    with app.state.session_factory() as session:
        process_article_text(session, article_id, max_segment_chars=14)
        result = process_article_audio(session, article_id, tts_client=tts_client, storage=storage)
        article = session.scalar(
            select(ArticleAudioItem).where(ArticleAudioItem.article_id == article_id)
        )
        segments = session.scalars(
            select(ArticleTtsSegment)
            .where(ArticleTtsSegment.article_id == article_id)
            .order_by(ArticleTtsSegment.segment_index)
        ).all()

    assert result.generated is True
    assert result.segment_count == 3
    assert result.storage_key == f"web2audio/articles/{article_id}/final.mp3"
    assert article is not None
    assert article.text_status == TEXT_READY
    assert article.audio_status == AUDIO_READY
    assert article.player_sync_status == PLAYER_PENDING
    assert article.audio_storage_key == result.storage_key
    assert article.duration_seconds == result.duration_seconds
    assert article.duration_seconds == sum(segment.duration_seconds for segment in segments)
    assert [segment.tts_status for segment in segments] == [AUDIO_READY, AUDIO_READY, AUDIO_READY]
    assert all(segment.audio_storage_key in storage.objects for segment in segments)
    assert article.audio_storage_key in storage.objects
    assert tts_client.requests == [segment.text_content for segment in segments]


def test_process_article_audio_marks_failed_when_text_is_not_ready(tmp_path: Path) -> None:
    db_url = f"sqlite:///{tmp_path / 'web2audio-test.db'}"
    app = create_app(database_url=db_url, auth_token=TOKEN)
    client = TestClient(app)
    created = client.post("/api/articles", json=article_payload(), headers=auth_headers())
    article_id = created.json()["article_id"]

    with app.state.session_factory() as session:
        result = process_article_audio(
            session,
            article_id,
            tts_client=FakeTtsClient(),
            storage=FakeTosStorage(),
        )
        article = session.scalar(
            select(ArticleAudioItem).where(ArticleAudioItem.article_id == article_id)
        )

    assert result.generated is False
    assert result.error_code == "text_not_ready"
    assert article is not None
    assert article.audio_status != AUDIO_READY
