from __future__ import annotations

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.love_song_contract import (  # noqa: E402
    FakeLoveSongClient,
    TosAssetRegistrationRequest,
)


def test_fake_love_song_client_registers_tos_asset_idempotently() -> None:
    client = FakeLoveSongClient()
    request = TosAssetRegistrationRequest(
        external_source="web2audio",
        external_id="art_123",
        content_type="article_audio",
        title="示例文章标题",
        subtitle="微信公众平台",
        cover_url="https://example.com/cover.jpg",
        duration_seconds=120,
        storage_key="web2audio/articles/art_123/final.mp3",
        mime_type="audio/mpeg",
    )

    first = client.register_tos_asset(request)
    second = client.register_tos_asset(request)

    assert first.created is True
    assert second.created is False
    assert first.track_id == second.track_id
    assert first.asset_id == second.asset_id
    assert second.content_type == "article_audio"
    assert second.subtitle == "微信公众平台"
    assert second.source_type == "tos"


def test_fake_love_song_client_appends_playlist_tracks_idempotently() -> None:
    client = FakeLoveSongClient()

    first = client.append_track_to_playlist("pl_today_reading", "track_abc")
    second = client.append_track_to_playlist("pl_today_reading", "track_abc")

    assert first.added is True
    assert second.added is False
    assert first.position == second.position == 0
    assert client.playlist_tracks["pl_today_reading"] == ["track_abc"]
