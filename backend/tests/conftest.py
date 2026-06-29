from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi import FastAPI
from sqlalchemy import delete, select


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import Settings  # noqa: E402
from app.main import ArticleAudioItem, ArticleTtsSegment, create_app  # noqa: E402


@pytest.fixture
def mysql_app_factory() -> Callable[..., FastAPI]:
    apps: list[tuple[FastAPI, str]] = []
    base_settings = Settings()
    database_url = base_settings.resolve_database_url()

    def factory(auth_token: str, **overrides: str) -> FastAPI:
        owner_user_id = overrides.pop("owner_user_id", f"test_{uuid4().hex}")
        runtime_settings = base_settings.model_copy(
            update={
                "database_url": database_url,
                "auth_token": auth_token,
                "owner_user_id": owner_user_id,
                **overrides,
            }
        )
        app = create_app(settings=runtime_settings)
        apps.append((app, owner_user_id))
        return app

    yield factory

    for app, owner_user_id in apps:
        with app.state.session_factory() as session:
            article_ids = select(ArticleAudioItem.article_id).where(
                ArticleAudioItem.owner_user_id == owner_user_id
            )
            session.execute(
                delete(ArticleTtsSegment).where(ArticleTtsSegment.article_id.in_(article_ids))
            )
            session.execute(
                delete(ArticleAudioItem).where(ArticleAudioItem.owner_user_id == owner_user_id)
            )
            session.commit()
        app.state.engine.dispose()
