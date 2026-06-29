from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.clients.love_song import HttpLoveSongClient  # noqa: E402
from app.love_song_contract import TosAssetRegistrationRequest  # noqa: E402


def test_http_love_song_client_registers_tos_asset_and_appends_playlist() -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content.decode("utf-8"))
        calls.append((request.method, request.url.path, payload))
        if request.url.path == "/api/assets/tos":
            return httpx.Response(
                201,
                json={
                    "track_id": "track_123",
                    "asset_id": "ast_123",
                    "content_type": "article_audio",
                    "title": payload["title"],
                    "subtitle": payload["subtitle"],
                    "source_type": "tos",
                },
            )
        if request.url.path == "/api/playlists/pl_today_reading/tracks":
            return httpx.Response(
                201,
                json={
                    "playlist_id": "pl_today_reading",
                    "track_id": payload["track_id"],
                    "position": 1,
                },
            )
        return httpx.Response(404, json={"error": {"code": "not_found"}})

    http_client = httpx.Client(
        base_url="http://love-song.test",
        transport=httpx.MockTransport(handler),
    )
    client = HttpLoveSongClient(
        base_url="http://love-song.test",
        service_token="service-token",
        http_client=http_client,
    )

    registered = client.register_tos_asset(
        TosAssetRegistrationRequest(
            external_source="web2audio",
            external_id="art_123",
            content_type="article_audio",
            title="文章标题",
            subtitle="微信公众平台",
            cover_url="https://example.com/cover.jpg",
            duration_seconds=120,
            storage_key="web2audio/articles/art_123/final.mp3",
            mime_type="audio/mpeg",
        )
    )
    appended = client.append_track_to_playlist("pl_today_reading", registered.track_id)

    assert registered.track_id == "track_123"
    assert registered.asset_id == "ast_123"
    assert registered.created is True
    assert appended.added is True
    assert appended.position == 1
    assert calls == [
        (
            "POST",
            "/api/assets/tos",
            {
                "external_source": "web2audio",
                "external_id": "art_123",
                "content_type": "article_audio",
                "title": "文章标题",
                "subtitle": "微信公众平台",
                "cover_url": "https://example.com/cover.jpg",
                "duration_seconds": 120,
                "storage_key": "web2audio/articles/art_123/final.mp3",
                "mime_type": "audio/mpeg",
            },
        ),
        (
            "POST",
            "/api/playlists/pl_today_reading/tracks",
            {"track_id": "track_123"},
        ),
    ]


def test_http_love_song_client_treats_duplicate_playlist_append_as_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            409,
            json={
                "error": {
                    "code": "track_already_in_playlist",
                    "message": "Track already in playlist.",
                    "details": {},
                }
            },
        )

    http_client = httpx.Client(
        base_url="http://love-song.test",
        transport=httpx.MockTransport(handler),
    )
    client = HttpLoveSongClient(
        base_url="http://love-song.test",
        service_token="service-token",
        http_client=http_client,
    )

    appended = client.append_track_to_playlist("pl_today_reading", "track_123")

    assert appended.added is False
    assert appended.playlist_id == "pl_today_reading"
    assert appended.track_id == "track_123"
    assert appended.position == 0
