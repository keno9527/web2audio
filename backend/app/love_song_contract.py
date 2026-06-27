from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


WEB2AUDIO_EXTERNAL_SOURCE = "web2audio"
ARTICLE_AUDIO_CONTENT_TYPE = "article_audio"
TOS_SOURCE_TYPE = "tos"


@dataclass(frozen=True)
class TosAssetRegistrationRequest:
    external_source: str
    external_id: str
    content_type: str
    title: str
    subtitle: Optional[str]
    cover_url: Optional[str]
    duration_seconds: int
    storage_key: str
    mime_type: str


@dataclass(frozen=True)
class TosAssetRegistrationResponse:
    track_id: str
    asset_id: str
    content_type: str
    title: str
    subtitle: Optional[str]
    source_type: str
    created: bool


@dataclass(frozen=True)
class PlaylistAppendResponse:
    playlist_id: str
    track_id: str
    position: int
    added: bool


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
