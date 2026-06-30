from __future__ import annotations

import logging
import sys
from pathlib import Path

from fastapi.testclient import TestClient


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.audio_jobs import process_article_audio  # noqa: E402
from app.clients.fake import FakeLoveSongClient, FakeTosStorage, FakeTtsClient  # noqa: E402
from app.player_sync_jobs import process_player_sync  # noqa: E402
from app.text_jobs import process_article_text  # noqa: E402


TOKEN = "test-token"
PLAYLIST_ID = "demo_playlist_focus"


def auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {TOKEN}"}


def article_payload() -> dict[str, str]:
    return {
        "source_url": "https://example.com/logging-pipeline",
        "title": "日志链路测试文章",
        "text_content": "第一段 内容足够长。\n\n第二段 内容也足够长。\n\n第三段结尾。",
        "site_name": "Example",
        "language_hint": "zh-CN",
    }


def pipeline_messages(caplog) -> str:
    return "\n".join(
        record.getMessage()
        for record in caplog.records
        if record.name == "web2audio.pipeline"
    )


def test_article_submission_logs_created_task_waiting_for_text_worker(
    mysql_app_factory,
    caplog,
) -> None:
    caplog.set_level(logging.INFO, logger="web2audio.pipeline")
    app = mysql_app_factory(TOKEN)
    client = TestClient(app)

    response = client.post("/api/articles", json=article_payload(), headers=auth_headers())

    assert response.status_code == 201
    article_id = response.json()["article_id"]
    messages = pipeline_messages(caplog)
    assert f"article_id={article_id}" in messages
    assert "event=article_task_created" in messages
    assert "stage=article_submission" in messages
    assert "text_status=queued" in messages
    assert "audio_status=pending" in messages
    assert "player_sync_status=pending" in messages
    assert "event=article_waiting_for_worker" in messages
    assert "next_stage=text_processing" in messages
    assert "event=text_processing_started" not in messages


def test_pipeline_jobs_emit_stage_logs_with_same_article_id(
    mysql_app_factory,
    caplog,
) -> None:
    caplog.set_level(logging.INFO, logger="web2audio.pipeline")
    app = mysql_app_factory(TOKEN)
    client = TestClient(app)
    created = client.post("/api/articles", json=article_payload(), headers=auth_headers())
    article_id = created.json()["article_id"]

    with app.state.session_factory() as session:
        process_article_text(session, article_id, max_segment_chars=14)
        process_article_audio(
            session,
            article_id,
            tts_client=FakeTtsClient(),
            storage=FakeTosStorage(),
        )
        process_player_sync(
            session,
            article_id,
            love_song_client=FakeLoveSongClient(),
            playlist_id=PLAYLIST_ID,
        )

    messages = pipeline_messages(caplog)
    assert messages.count(f"article_id={article_id}") >= 7
    for expected in (
        "event=text_processing_started stage=text_processing",
        "event=text_processing_ready stage=text_processing",
        "event=audio_generation_started stage=audio_generation",
        "event=audio_generation_ready stage=audio_generation",
        "event=player_sync_started stage=player_sync",
        "event=player_sync_ready stage=player_sync",
    ):
        assert expected in messages
    assert "segment_count=3" in messages
    assert f"playlist_id={PLAYLIST_ID}" in messages
