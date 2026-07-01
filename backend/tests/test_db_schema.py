from __future__ import annotations

import sys
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.schema import ensure_database_schema  # noqa: E402


def test_ensure_database_schema_creates_article_tables_indexes_and_constraints(
) -> None:
    engine = ensure_database_schema()
    suffix = uuid4().hex

    inspector = inspect(engine)
    assert set(inspector.get_table_names()) >= {
        "article_audio_items",
        "article_tts_segments",
    }

    article_indexes = {index["name"] for index in inspector.get_indexes("article_audio_items")}
    assert "idx_article_audio_items_owner_status" in article_indexes
    assert "idx_article_audio_items_love_song_track_id" in article_indexes

    segment_indexes = {index["name"] for index in inspector.get_indexes("article_tts_segments")}
    assert "idx_article_tts_segments_article_status" in segment_indexes

    article_checks = {
        constraint["name"]
        for constraint in inspector.get_check_constraints("article_audio_items")
    }
    assert "ck_article_audio_items_text_status" in article_checks
    assert "ck_article_audio_items_audio_status" in article_checks
    assert "ck_article_audio_items_player_sync_status" in article_checks

    segment_checks = {
        constraint["name"]
        for constraint in inspector.get_check_constraints("article_tts_segments")
    }
    assert "ck_article_tts_segments_tts_status" in segment_checks

    try:
        with engine.begin() as connection:
            with pytest.raises(SQLAlchemyError):
                connection.execute(
                    text(
                        """
                        INSERT INTO article_audio_items (
                          article_id, owner_user_id, source_url, source_url_hash, title,
                          text_char_count,
                          text_status, audio_status, player_sync_status,
                          submitted_at, created_at, updated_at
                        )
                        VALUES (
                          :article_id, :owner_user_id, :source_url, :source_url_hash,
                          'Bad status', 0, 9, 0, 0,
                          CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                        )
                        """
                    ),
                    {
                        "article_id": f"art_bad_status_{suffix}",
                        "owner_user_id": f"test_{suffix}",
                        "source_url": f"https://example.com/{suffix}",
                        "source_url_hash": f"hash_{suffix}",
                    },
                )

        with engine.begin() as connection:
            with pytest.raises(SQLAlchemyError):
                connection.execute(
                    text(
                        """
                        INSERT INTO article_tts_segments (
                          segment_id, article_id, segment_index, text_content, text_char_count,
                          tts_status, created_at, updated_at
                        )
                        VALUES (
                          :segment_id, :article_id, 0, 'orphan text', 11,
                          0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                        )
                        """
                    ),
                    {
                        "segment_id": f"seg_orphan_{suffix}",
                        "article_id": f"art_missing_{suffix}",
                    },
                )
    finally:
        with engine.begin() as connection:
            connection.execute(
                text("DELETE FROM article_tts_segments WHERE segment_id = :segment_id"),
                {"segment_id": f"seg_orphan_{suffix}"},
            )
            connection.execute(
                text("DELETE FROM article_audio_items WHERE article_id = :article_id"),
                {"article_id": f"art_bad_status_{suffix}"},
            )
        engine.dispose()
