from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import create_app  # noqa: E402
from app.self_test import fake_article_payload, run_fake_full_chain  # noqa: E402


TOKEN = "test-token"
PLAYLIST_ID = "pl_today_reading"


def auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {TOKEN}"}


def test_fake_full_chain_reaches_playable_article_state(tmp_path: Path) -> None:
    db_url = f"sqlite:///{tmp_path / 'web2audio-test.db'}"
    app = create_app(database_url=db_url, auth_token=TOKEN)
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
