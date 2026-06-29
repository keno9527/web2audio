from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import text


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import Settings  # noqa: E402
from app.db.session import create_engine_and_session_factory  # noqa: E402


def test_db_session_factory_uses_mysql_connection() -> None:
    engine, session_factory = create_engine_and_session_factory(Settings().resolve_database_url())

    assert engine.url.get_backend_name() == "mysql"

    with session_factory() as session:
        assert session.execute(text("SELECT 1")).scalar_one() == 1

    engine.dispose()


def test_create_app_accepts_settings_object(mysql_app_factory) -> None:
    app = mysql_app_factory("test-token", app_name="web2audio-test")
    client = TestClient(app)

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert app.state.settings.app_name == "web2audio-test"
