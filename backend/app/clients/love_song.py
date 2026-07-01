from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping, Optional, Protocol

import httpx

from app.love_song_contract import (
    TOS_SOURCE_TYPE,
    PlaylistAppendResponse,
    TosAssetRegistrationRequest,
    TosAssetRegistrationResponse,
)


class LoveSongClient(Protocol):
    def register_tos_asset(
        self, request: TosAssetRegistrationRequest
    ) -> TosAssetRegistrationResponse:
        """Register a TOS object as a playable love-song asset."""

    def append_track_to_playlist(
        self, playlist_id: str, track_id: str
    ) -> PlaylistAppendResponse:
        """Append a track to a playlist. Duplicate appends should be idempotent."""


@dataclass(frozen=True)
class LoveSongHttpConfig:
    base_url: str
    service_token: str = ""
    timeout: float = 10.0

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "LoveSongHttpConfig":
        return cls(
            base_url=str(data.get("base_url") or ""),
            service_token=str(data.get("service_token") or ""),
            timeout=float(data.get("timeout") or 10),
        )

    def validate(self) -> None:
        if not self.base_url:
            raise ValueError("love-song config missing required fields: base_url")


class LoveSongClientError(Exception):
    pass


class HttpLoveSongClient:
    def __init__(
        self,
        base_url: str,
        service_token: str = "",
        timeout: float = 10.0,
        http_client: Optional[httpx.Client] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.service_token = service_token
        self._http = http_client or httpx.Client(base_url=self.base_url, timeout=timeout)

    @classmethod
    def from_config(
        cls,
        config: LoveSongHttpConfig,
        http_client: Optional[httpx.Client] = None,
    ) -> "HttpLoveSongClient":
        config.validate()
        return cls(
            base_url=config.base_url,
            service_token=config.service_token,
            timeout=config.timeout,
            http_client=http_client,
        )

    def _headers(self) -> dict[str, str]:
        if not self.service_token:
            return {}
        return {"Authorization": f"Bearer {self.service_token}"}

    def register_tos_asset(
        self, request: TosAssetRegistrationRequest
    ) -> TosAssetRegistrationResponse:
        response = self._http.post(
            "/api/assets/tos",
            json=asdict(request),
            headers=self._headers(),
        )
        if response.status_code not in {200, 201}:
            raise LoveSongClientError(
                f"love-song asset registration failed: {response.status_code}"
            )
        body = response.json()
        return TosAssetRegistrationResponse(
            track_id=str(body["track_id"]),
            asset_id=str(body["asset_id"]),
            content_type=str(body.get("content_type") or request.content_type),
            title=str(body.get("title") or request.title),
            subtitle=body.get("subtitle") if body.get("subtitle") is not None else request.subtitle,
            source_type=str(body.get("source_type") or TOS_SOURCE_TYPE),
            created=response.status_code == 201,
        )

    def append_track_to_playlist(
        self, playlist_id: str, track_id: str
    ) -> PlaylistAppendResponse:
        response = self._http.post(
            f"/api/playlists/{playlist_id}/tracks",
            json={"track_id": track_id},
            headers=self._headers(),
        )
        if response.status_code == 409 and self._error_code(response) == "track_already_in_playlist":
            return PlaylistAppendResponse(
                playlist_id=playlist_id,
                track_id=track_id,
                position=0,
                added=False,
            )
        if response.status_code not in {200, 201}:
            raise LoveSongClientError(f"love-song playlist append failed: {response.status_code}")
        body = response.json()
        return PlaylistAppendResponse(
            playlist_id=str(body.get("playlist_id") or playlist_id),
            track_id=str(body.get("track_id") or track_id),
            position=int(body.get("position") or 0),
            added=response.status_code == 201,
        )

    @staticmethod
    def _error_code(response: httpx.Response) -> str:
        try:
            body = response.json()
        except ValueError:
            return ""
        error = body.get("error")
        if not isinstance(error, dict):
            return ""
        return str(error.get("code") or "")
