from __future__ import annotations

from typing import Optional

from sqlalchemy.engine import Engine
from sqlalchemy import text

from app.core.config import Settings, settings as default_settings
from app.db.session import create_engine_and_session_factory
from app.main import Base


def ensure_database_schema(
    database_url: Optional[str] = None,
    settings: Optional[Settings] = None,
) -> Engine:
    runtime_settings = settings or default_settings
    resolved_database_url = database_url or runtime_settings.resolve_database_url()
    engine, _ = create_engine_and_session_factory(resolved_database_url)
    Base.metadata.create_all(engine)
    _ensure_mysql_schema_details(engine)
    return engine


def _ensure_mysql_schema_details(engine: Engine) -> None:
    if engine.url.get_backend_name() != "mysql":
        raise ValueError("web2audio database schema must be initialized on MySQL")

    with engine.begin() as connection:
        database_name = connection.execute(text("SELECT DATABASE()")).scalar_one()

        existing_indexes = {
            (row.table_name, row.index_name)
            for row in connection.execute(
                text(
                    """
                    SELECT TABLE_NAME AS table_name, INDEX_NAME AS index_name
                    FROM information_schema.STATISTICS
                    WHERE TABLE_SCHEMA = :database_name
                      AND TABLE_NAME IN ('article_audio_items', 'article_tts_segments')
                    """
                ),
                {"database_name": database_name},
            )
        }
        existing_constraints = {
            (row.table_name, row.constraint_name)
            for row in connection.execute(
                text(
                    """
                    SELECT TABLE_NAME AS table_name, CONSTRAINT_NAME AS constraint_name
                    FROM information_schema.TABLE_CONSTRAINTS
                    WHERE CONSTRAINT_SCHEMA = :database_name
                      AND TABLE_NAME IN ('article_audio_items', 'article_tts_segments')
                    """
                ),
                {"database_name": database_name},
            )
        }
        _add_unique_if_missing(
            connection,
            existing_constraints,
            "article_audio_items",
            "uq_article_audio_items_article_id",
            "article_id",
        )
        _add_unique_if_missing(
            connection,
            existing_constraints,
            "article_audio_items",
            "uq_article_audio_items_owner_source_hash",
            "owner_user_id, source_url_hash",
        )
        _add_unique_if_missing(
            connection,
            existing_constraints,
            "article_tts_segments",
            "uq_article_tts_segments_segment_id",
            "segment_id",
        )
        _add_unique_if_missing(
            connection,
            existing_constraints,
            "article_tts_segments",
            "uq_article_tts_segments_article_index",
            "article_id, segment_index",
        )
        _add_index_if_missing(
            connection,
            existing_indexes,
            "article_audio_items",
            "idx_article_audio_items_owner_status",
            "owner_user_id, text_status, audio_status, player_sync_status, updated_at",
        )
        _add_index_if_missing(
            connection,
            existing_indexes,
            "article_audio_items",
            "idx_article_audio_items_love_song_track_id",
            "love_song_track_id",
        )
        _add_index_if_missing(
            connection,
            existing_indexes,
            "article_tts_segments",
            "idx_article_tts_segments_article_status",
            "article_id, tts_status, segment_index",
        )

        existing_checks = {
            row.constraint_name
            for row in connection.execute(
                text(
                    """
                    SELECT CONSTRAINT_NAME AS constraint_name
                    FROM information_schema.CHECK_CONSTRAINTS
                    WHERE CONSTRAINT_SCHEMA = :database_name
                    """
                ),
                {"database_name": database_name},
            )
        }
        _add_check_if_missing(
            connection,
            existing_checks,
            "article_audio_items",
            "ck_article_audio_items_text_status",
            "text_status IN (0, 1, 2, 3)",
        )
        _add_check_if_missing(
            connection,
            existing_checks,
            "article_audio_items",
            "ck_article_audio_items_audio_status",
            "audio_status IN (0, 1, 2, 3)",
        )
        _add_check_if_missing(
            connection,
            existing_checks,
            "article_audio_items",
            "ck_article_audio_items_player_sync_status",
            "player_sync_status IN (0, 1, 2, 3)",
        )
        _add_check_if_missing(
            connection,
            existing_checks,
            "article_tts_segments",
            "ck_article_tts_segments_tts_status",
            "tts_status IN (0, 1, 2, 3)",
        )
        existing_foreign_keys = {
            (
                row.table_name,
                row.columns,
                row.referenced_table_name,
                row.referenced_columns,
            )
            for row in connection.execute(
                text(
                    """
                    SELECT
                      TABLE_NAME AS table_name,
                      GROUP_CONCAT(COLUMN_NAME ORDER BY ORDINAL_POSITION) AS columns,
                      REFERENCED_TABLE_NAME AS referenced_table_name,
                      GROUP_CONCAT(
                        REFERENCED_COLUMN_NAME
                        ORDER BY POSITION_IN_UNIQUE_CONSTRAINT
                      ) AS referenced_columns
                    FROM information_schema.KEY_COLUMN_USAGE
                    WHERE TABLE_SCHEMA = :database_name
                      AND TABLE_NAME = 'article_tts_segments'
                      AND REFERENCED_TABLE_NAME IS NOT NULL
                    GROUP BY TABLE_NAME, CONSTRAINT_NAME, REFERENCED_TABLE_NAME
                    """
                ),
                {"database_name": database_name},
            )
        }
        _add_foreign_key_if_missing(
            connection,
            existing_foreign_keys,
            "article_tts_segments",
            "article_id",
            "article_audio_items",
            "article_id",
            "fk_article_tts_segments_article_id",
            "CASCADE",
            "CASCADE",
        )


def _add_index_if_missing(
    connection,
    existing_indexes: set[tuple[str, str]],
    table_name: str,
    index_name: str,
    columns_sql: str,
) -> None:
    if (table_name, index_name) in existing_indexes:
        return
    connection.exec_driver_sql(f"ALTER TABLE {table_name} ADD INDEX {index_name} ({columns_sql})")


def _add_unique_if_missing(
    connection,
    existing_constraints: set[tuple[str, str]],
    table_name: str,
    constraint_name: str,
    columns_sql: str,
) -> None:
    if (table_name, constraint_name) in existing_constraints:
        return
    connection.exec_driver_sql(
        f"ALTER TABLE {table_name} ADD CONSTRAINT {constraint_name} UNIQUE ({columns_sql})"
    )


def _add_check_if_missing(
    connection,
    existing_checks: set[str],
    table_name: str,
    constraint_name: str,
    condition_sql: str,
) -> None:
    if constraint_name in existing_checks:
        return
    connection.exec_driver_sql(
        f"ALTER TABLE {table_name} ADD CONSTRAINT {constraint_name} CHECK ({condition_sql})"
    )


def _add_foreign_key_if_missing(
    connection,
    existing_foreign_keys: set[tuple[str, str, str, str]],
    table_name: str,
    columns_sql: str,
    referenced_table_name: str,
    referenced_columns_sql: str,
    constraint_name: str,
    on_update: str,
    on_delete: str,
) -> None:
    if (
        table_name,
        columns_sql.replace(" ", ""),
        referenced_table_name,
        referenced_columns_sql.replace(" ", ""),
    ) in existing_foreign_keys:
        return
    connection.exec_driver_sql(
        (
            f"ALTER TABLE {table_name} ADD CONSTRAINT {constraint_name} "
            f"FOREIGN KEY ({columns_sql}) REFERENCES {referenced_table_name} "
            f"({referenced_columns_sql}) ON UPDATE {on_update} ON DELETE {on_delete}"
        )
    )
