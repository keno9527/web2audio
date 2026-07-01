from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


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
