from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import (  # noqa: E402
    AUDIO_PENDING,
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
        "title": "待清洗文章",
        "text_content": "  第一段  内容足够长。\n\n第二段 内容也足够长。\n\n第三段结尾。",
        "site_name": "微信公众平台",
        "language_hint": "zh-CN",
    }


def test_process_article_text_writes_clean_body_segments_and_ready_status(tmp_path: Path) -> None:
    db_url = f"sqlite:///{tmp_path / 'web2audio-test.db'}"
    app = create_app(database_url=db_url, auth_token=TOKEN)
    client = TestClient(app)
    created = client.post("/api/articles", json=article_payload(), headers=auth_headers())
    article_id = created.json()["article_id"]

    with app.state.session_factory() as session:
        result = process_article_text(session, article_id, max_segment_chars=14)
        article = session.scalar(
            select(ArticleAudioItem).where(ArticleAudioItem.article_id == article_id)
        )
        segments = session.scalars(
            select(ArticleTtsSegment)
            .where(ArticleTtsSegment.article_id == article_id)
            .order_by(ArticleTtsSegment.segment_index)
        ).all()

    assert result.processed is True
    assert result.segment_count == 3
    assert article is not None
    assert article.text_status == TEXT_READY
    assert article.audio_status == AUDIO_PENDING
    assert article.player_sync_status == PLAYER_PENDING
    assert article.language == "zh"
    assert article.text_content == "第一段 内容足够长。\n第二段 内容也足够长。\n第三段结尾。"
    assert [segment.segment_index for segment in segments] == [0, 1, 2]
    assert [segment.text_content for segment in segments] == [
        "第一段 内容足够长。",
        "第二段 内容也足够长。",
        "第三段结尾。",
    ]
