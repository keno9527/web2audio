from __future__ import annotations

import hashlib
from typing import Dict, List, Optional, Tuple

from app.clients.tts import AudioSynthesisResult
from app.love_song_contract import (
    TOS_SOURCE_TYPE,
    PlaylistAppendResponse,
    TosAssetRegistrationRequest,
    TosAssetRegistrationResponse,
)


class FakeTtsClient:
    def __init__(self, duration_seconds_per_char: float = 0.2) -> None:
        self.duration_seconds_per_char = duration_seconds_per_char
        self.requests: list[str] = []

    def synthesize(self, text: str, language: Optional[str] = None) -> AudioSynthesisResult:
        self.requests.append(text)
        duration = max(1, int(round(len(text) * self.duration_seconds_per_char)))
        payload = f"FAKE-MP3[{language or 'unknown'}]:{text}".encode("utf-8")
        return AudioSynthesisResult(content=payload, duration_seconds=duration)


class FakeTosStorage:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.content_types: dict[str, str] = {}

    def put_object(self, key: str, content: bytes, content_type: str) -> str:
        self.objects[key] = content
        self.content_types[key] = content_type
        return key


def stable_love_song_id(prefix: str, value: str) -> str:
    suffix = hashlib.sha256(value.encode("utf-8")).hexdigest()[:20]
    return f"{prefix}_{suffix}"


class FakeLoveSongClient:
    def __init__(self) -> None:
        self.assets: Dict[Tuple[str, str], TosAssetRegistrationResponse] = {}
        self.playlist_tracks: Dict[str, List[str]] = {}

    def register_tos_asset(
        self, request: TosAssetRegistrationRequest
    ) -> TosAssetRegistrationResponse:
        idempotency_key = (request.external_source, request.external_id)
        existing = self.assets.get(idempotency_key)
        if existing is not None:
            return TosAssetRegistrationResponse(
                track_id=existing.track_id,
                asset_id=existing.asset_id,
                content_type=existing.content_type,
                title=existing.title,
                subtitle=existing.subtitle,
                source_type=existing.source_type,
                created=False,
            )

        stable_key = f"{request.external_source}:{request.external_id}"
        response = TosAssetRegistrationResponse(
            track_id=stable_love_song_id("track", stable_key),
            asset_id=stable_love_song_id("ast", stable_key),
            content_type=request.content_type,
            title=request.title,
            subtitle=request.subtitle,
            source_type=TOS_SOURCE_TYPE,
            created=True,
        )
        self.assets[idempotency_key] = response
        return response

    def append_track_to_playlist(
        self, playlist_id: str, track_id: str
    ) -> PlaylistAppendResponse:
        tracks = self.playlist_tracks.setdefault(playlist_id, [])
        if track_id in tracks:
            return PlaylistAppendResponse(
                playlist_id=playlist_id,
                track_id=track_id,
                position=tracks.index(track_id),
                added=False,
            )
        tracks.append(track_id)
        return PlaylistAppendResponse(
            playlist_id=playlist_id,
            track_id=track_id,
            position=len(tracks) - 1,
            added=True,
        )
